# Copyright (c) 2025,  IEIT SYSTEMS Co.,Ltd.  All rights reserved

# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at

#     http://www.apache.org/licenses/LICENSE-2.0

# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

import copy
from sqlalchemy import create_engine
from .base_diagnosis_request_handler import BaseDiagnosisRequestHandler
from .prompt_template import *
from .util_data_models import *
from .util_sqlite_function import *
from .util import *
import io
from fastapi.responses import StreamingResponse, JSONResponse
from pydantic import ValidationError
from fastapi import HTTPException
import concurrent.futures

DISEASE_WEIGHT_RULES={}
#参考写法：
#DISEASE_WEIGHT_RULES = {
#    "头痛": {"脑血管病介入科门诊": 1.7},
#    "头晕":{"脑血管病介入科门诊": 1.7},
#    "癌":{"日间化疗中心":2.0},
 #   "胃纳":{"中医科门诊":3.0}
#    # 其他疾病规则...
#}

class HospitalGuideProcessChecker:
    def __init__(self, receive) -> None:
        self.bmr = receive.output.basic_medical_record

    def __check_chief_complaint(self):
        return any(getattr(self.bmr, attr) in ["", None] for attr in
            ['chief_complaint', 'history_of_present_illness', 'past_medical_history', 'personal_history', 'allergy_history'])

    def check(self) -> int:
        if self.__check_chief_complaint(): return 81
        else: return 8

class HospitalGuideRequestHandler(BaseDiagnosisRequestHandler):
    def __init__(self,
                 receive,
                 args,
                 scheme : None,
                 sub_scheme : None,
                 request_type: None,
                 enable_think: False
                 ):
        super().__init__(receive, args, scheme, sub_scheme, request_type, enable_think)
        try:
            self.receive = RequestV8(**receive)
        except ValidationError as e:
            raise HTTPException(status_code=422, detail=e.errors())
        self.db_engine = create_engine(f"sqlite:///{self.args.database}/medical_assistant.db")

    def checker_flag(self):
        self.checker = HospitalGuideProcessChecker(self.receive)
        self.flag = self.checker.check()

    def generate_prompt(self):
        self.prompt = get_prompt('PromptHospitalGuide', self.receive, self.db_engine, self.scheme, )
        self.prompt.set_prompt()

    def postprocess(self, messages):
        answer=""
        answers = self.predict_stream(messages, self.temprature, self.top_p)
        for re in answers:
            answer+=re
            yield re
        results = self.postprocess_hg(self.receive, answer, self.scheme)

        if department_recommend in answer:
            top_departments = self.department_recommend(results)
            results = self.postprocess_hg(results, top_departments, self.scheme)

        results_dict = results.model_dump()
        results_json = json.dumps(results_dict, ensure_ascii=False)
        results=str(results_json)
        results = results.encode('utf-8')
        results = io.BytesIO(results)
        for re in results:
            yield re
        return

    def postprocess_hg(self, receive, answer, scheme):
        params = copy.deepcopy(receive)
        hc = params.chat.historical_conversations
        hc_bak = params.chat.historical_conversations_bak
        if type(answer) is not list:
            if hc != [] and hc[-1].role == 'user':
                hc_bak.append(HistoricalConversations(role='user', content=hc[-1].content))
            hc.append(HistoricalConversations(role='assistant', content=answer))
            hc_bak.append(HistoricalConversations(role='assistant', content=answer))

            json_match, text_match = extract_json_and_text(answer)
            if not isinstance(json_match, re.Match):
                return params
            else:
                try:
                    json_data = json_match.group(0)
                    json_data = eval(json_data)
                    # print(f"大模型匹配内容: \n{json_data=}\n")
                except:
                    print("Error: There is no matching json data.")
                    return params
        else:
            department_item = []
            text = f"""根据您的主要症状，推荐您在如下科室就诊，期待您的早日康复！\n
患者病情：\n【主诉】: {params.output.basic_medical_record.chief_complaint}\n\n推荐科室："""
            all_department = [{"department_id":v.department_id, "department_name":v.department_name, "if_child":v.if_child}
                              for v in self.receive.input.all_department]
            for query_item in answer:
                search_result = list(filter(lambda item: query_item in item['department_name'], all_department))
                if search_result:
                    department_item.append(Department2(
                        department_id=search_result[0]['department_id'],
                        department_name=search_result[0]['department_name'],
                        if_child=search_result[0]['if_child']
                    ))
                    text += f"""\n【{search_result[0]['department_name']}】"""
            params.output.chosen_department = department_item
            hc.pop()
            hc_bak.pop()
            hc.append(HistoricalConversations(role='assistant', content=text))
            hc_bak.append(HistoricalConversations(role='assistant', content=text))
            return params

        match scheme:
            case "simple":
                if '病历' in json_data and json_data['病历']:
                    params.output.basic_medical_record.chief_complaint = json_data['病历']['主诉']

            case "detailed":
                params.output.basic_medical_record.chief_complaint = json_data['主诉']
                params.output.basic_medical_record.history_of_present_illness = json_data['现病史']
                params.output.basic_medical_record.past_medical_history = json_data['既往史']
                params.output.basic_medical_record.personal_history = json_data['个人史']
                params.output.basic_medical_record.allergy_history = json_data['过敏史']

                answer = self.format_basic_medical_record(json_data, text_match)
                hc.pop()
                hc.append(HistoricalConversations(role='assistant', content=answer))
 
        return params

    def format_basic_medical_record(self, json_data, text_match):
        #answer = f"""{text_match}
        answer = f"""依据您回复的情况，已经为您生成了预问诊报告，如无问题，请点击确认，如还需要补充请直接回复补充。
主诉: {json_data['主诉']}
现病史: {json_data['现病史']}
既往史: {json_data['既往史']}
个人史: {json_data['个人史']}
过敏史: {json_data['过敏史']}
"""
        return answer

    def department_recommend(self, params):
        #全部科室简介
        if int(params.input.client_info[0].patient.patient_age) < 6:
            department_intro = department_introduction(self.args.department_path, if_child=1)
        else:
            department_intro = department_introduction(self.args.department_path)

        #分组科室
        group_size = 5
        groups = [department_intro[i:i+group_size] for i in range(0, len(department_intro), group_size)]
        print(f'{group_size=}')
        print(f'{len(groups)=}')

        all_scores = {}
        group_responses = []
        #单线程
        #for i, group in enumerate(groups):
        #    scores,  response_text = self.evaluate_group_confidence(params, group)
        #    all_scores.update(scores)  # 合并所有科室得分
        #    group_responses.append(response_text)

        #多线程
        with concurrent.futures.ThreadPoolExecutor() as executor:
            # 提交所有任务
            future_to_group = {
                executor.submit(self.evaluate_group_confidence, params, group): group for group in groups
            }
            # 收集结果
            for future in concurrent.futures.as_completed(future_to_group):
                scores, response_text = future.result()
                all_scores.update(scores)
                group_responses.append(response_text)

        sorted_departments = sorted(
            all_scores.items(),
            key=lambda x: x[1],
            reverse=True
        )
        top_departments = [dept[0] for dept in sorted_departments[:3]]

        return top_departments

    def evaluate_group_confidence(self, params, group):
        #prompt
        #group department
        prompt = get_prompt('PromptHospitalGuide', params, self.db_engine, self.scheme, group)
        prompt.set_prompt()
        messages = self.preprocess(params, prompt, 82)
        answer = self.predict(messages, self.temprature, self.top_p)
        #response_text = answer.choices[0].message.content.strip()
        response_text = answer.strip()

        # 尝试解析JSON格式的响应
        scores = {}
        try:
            # 提取JSON部分
            json_match = re.search(r'\{.*\}', response_text, re.DOTALL)
            if json_match:
                json_str = json_match.group()
                score_dict = json.loads(json_str)

                # 匹配科室名称（允许部分匹配）
                for item in group:
                    for dept_name, intro in item.items():
                        # 检查完整名称或部分匹配
                        for resp_dept, score in score_dict.items():
                            if dept_name in resp_dept or resp_dept in dept_name:
                                scores[dept_name] = float(score)
                                break
        except json.JSONDecodeError:
                print("JSON解析失败，尝试行格式解析")

        # 如果JSON解析失败或没有匹配到足够科室，尝试解析行格式
        if len(scores) < len(group):
            lines = response_text.strip().split('\n')
            for line in lines:
                # 尝试匹配格式："科室名称: 分数"
                match = re.match(r'^\s*([^:]+):\s*(\d+(?:\.\d+)?)\s*$', line)
                if match:
                    resp_dept = match.group(1).strip()
                    score = float(match.group(2))

                    # 找到最匹配的实际科室名称
                    for item in group:
                        for dept_name, intro in item.items():
                            if dept_name in resp_dept or resp_dept in dept_name:
                                scores[dept_name] = score
                                break

        # 确保所有科室都有分数，未评分的默认为0
        for item in group:
            for dept_name, intro in item.items():
                if dept_name not in scores:
                    scores[dept_name] = 0.0

        # 对每个科室应用权重调整
        adjusted_scores = {}

        patient = params.input.client_info[0].patient
        chief_complaint = params.output.basic_medical_record.chief_complaint
        text=f"患者年龄：{patient.patient_age}\n患者性别{patient.patient_gender}\n患者主诉：{chief_complaint}"
        for dept_name, score in scores.items():
            weight = 1.0  # 默认权重
            # 检查是否匹配疾病权重规则
            disease_keywords = []
            text = text.lower()
            # 检查是否包含规则中的疾病关键词
            for disease in DISEASE_WEIGHT_RULES.keys():
                if disease in text:
                    disease_keywords.append(disease)

            for keyword in disease_keywords:
                if keyword in DISEASE_WEIGHT_RULES:
                    dept_weight = DISEASE_WEIGHT_RULES[keyword].get(dept_name, 1.0)
                    weight = max(weight, dept_weight)  # 取最大权重
            adjusted_scores[dept_name] = 0.3 * score * weight + 0.7 * score

        return adjusted_scores, response_text
