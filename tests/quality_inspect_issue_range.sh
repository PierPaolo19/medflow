# 1. 返回字段新增
#    1. issue_type:str 单位检查/拼写检查/阈值检查/遗漏检查
#    2. issue_index_range:List[Tuple[int,int]] 左闭右开
#    3. 新增doc字段，fields代替field传入多个检查字段
# 2. 输出内容
#    1. 由于'问题出处'需要基于原文，因此当输入多个fields输入，输出结果进行展开，比如["体温", "主诉"]规则会输出两个结果
curl -X 'POST' \
  'http://127.0.0.1:9111/quality_inspect' \
  -H 'accept: application/json' \
  -H 'Content-Type: application/json' \
  -d '
{
    "input": {
        "basic_medical_record": {
            "chief_complaint": "神志模糊、呕吐1⼩时、检测过体温是38，⾎压是100/70，有糖尿病",
            "history_of_present_illness": "1⼩时前饮酒后出现神志模糊，伴呕吐⾮咖啡⾊",
            "past_medical_history": "既往⾼⾎压病史1个⽉，规律服药治疗",
            "personal_history": "否认吸烟、有饮酒史",
            "allergy_history": "否认药物和⾷物过敏史",
            "physical_examination": {
                "temperature": "36.7℃",
                "pulse": "",
                "blood_pressure": "99/73mmHg",
                "respiration": "200次/分"
            },
            "auxiliary_examination": ""
        },
        "control_quality": [
            {
                "content": "体温单位",
                "doc": "门诊病历",
                "fields": ["体温", "主诉"],
                "standard": "数值后必须带℃，正确格式36.8℃，错误格式36.1",
                "auto_modify_type": true
            },
            {
                "content": "主诉内容",
                "doc": "门诊病历",
                "fields": ["主诉"],
                "standard": "检查有糖尿病的情况下，是否有明确描述⽬前⾎糖的情况",
                "auto_modify_type": true
            },
            {
                "content": "体温的数值是否符合标准",
                "doc": "门诊病历",
                "fields": ["体温"],
                "standard": "35.1~43.0 ℃包含边界值，比如35.1℃是正确的，35.0℃是错误的",
                "auto_modify_type": false
            }
        ]
    }
}
'

#测试结果
# {
#   "output": {
#     "basic_medical_record": {
#       "chief_complaint": "神志模糊、呕吐1⼩时、检测过体温是38，⾎压是100/70，有糖尿病",  # "主诉"
#       "history_of_present_illness": "1⼩时前饮酒后出现神志模糊，伴呕吐⾮咖啡⾊",        # "现病史"
#       "past_medical_history": "既往⾼⾎压病史1个⽉，规律服药治疗",                     # "既往史"
#       "personal_history": "否认吸烟、有饮酒史",                                       # "个人史"
#       "allergy_history": "否认药物和⾷物过敏史",                                      # "过敏史"
#       "physical_examination": {                                                     # "体格检查"
#         "temperature": "36.7℃",                                                    # "体温"
#         "pulse": "",                                                                # "脉搏"
#         "blood_pressure": "99/73mmHg",                                              # "血压"
#         "respiration": "200次/分"                                                   # "呼吸"
#       },
#       "auxiliary_examination": ""                                                   # "辅助检查"
#     },
#     "control_quality": [
#       {
#         "doc": "门诊病历",
#         "ref_doc": "",
#         "content": "体温单位",
#         "field": "主诉",
#         "fields": [
#           "体温",
#           "主诉"
#         ],
#         "ref_fields": [],
#         "item": "",
#         "standard": "数值后必须带℃，正确格式36.8℃，错误格式36.1",
#         "check_quality": "不通过    体温数值后未标注℃单位",
#         "auto_modify_type": true,
#         "auto_modify_info": "检测过体温是38℃",
#         "check_quality_detaile": "体温数值后未标注℃单位",
#         "amend_advice": "检测过体温是38℃",
#         "field_text": "神志模糊、呕吐1⼩时、检测过体温是38，⾎压是100/70，有糖尿病",
#         "issue_index_range": [
#           [
#             14,
#             19
#           ]
#         ],
#         "issue_type": "单位检查"
#       },
#       {
#         "doc": "门诊病历",
#         "ref_doc": "",
#         "content": "主诉内容",
#         "field": "主诉",
#         "fields": [
#           "主诉"
#         ],
#         "ref_fields": [],
#         "item": "",
#         "standard": "检查有糖尿病的情况下，是否有明确描述⽬前⾎糖的情况",
#         "check_quality": "不通过    未明确描述糖尿病患者的当前血糖数值或相关血糖状态",
#         "auto_modify_type": true,
#         "auto_modify_info": "在'有糖尿病'后补充具体血糖数值或症状，例如'空腹血糖12mmol/L'或'出现多尿、口渴等症状'",
#         "check_quality_detaile": "未明确描述糖尿病患者的当前血糖数值或相关血糖状态",
#         "amend_advice": "在'有糖尿病'后补充具体血糖数值或症状，例如'空腹血糖12mmol/L'或'出现多尿、口渴等症状'",
#         "field_text": "神志模糊、呕吐1⼩时、检测过体温是38，⾎压是100/70，有糖尿病",
#         "issue_index_range": [
#           [
#             30,
#             34
#           ]
#         ],
#         "issue_type": "遗漏检查"
#       }
#     ]
#   }
# }