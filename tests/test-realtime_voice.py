import asyncio
import json
import logging
from pathlib import Path

import websockets

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("transcription")


async def realtime_transcription(uri: str, audio_file: str = None):
    try:
        async with websockets.connect(uri) as websocket:
            logger.info(f"Connected to WebSocket server: {uri}")

            if audio_file and Path(audio_file).exists():
                logger.info(f"Reading the audio file: {audio_file}")

                with open(audio_file, "rb") as f:
                    audio_data = f.read()

                chunk_size = 8192

                for i in range(0, len(audio_data), chunk_size):
                    chunk = audio_data[i : i + chunk_size]
                    await websocket.send(chunk)
                    logger.info(f"Audio block has been sent: {i // chunk_size + 1}")
            else:
                logger.info(f"No File {audio_file}.")

            try:
                while True:
                    response = await asyncio.wait_for(websocket.recv(), timeout=10)
                    response = json.loads(response)
                    if response["type"] == "TranscriptionResponse":
                        logger.info(
                            f"Received the transcription results: {response['data']['final_text']}"
                        )

            except asyncio.TimeoutError:
                logger.info("Timeout.")

    except Exception as e:
        logger.error(f"Error: {str(e)}", exc_info=True)


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="Realtime Voice")
    parser.add_argument(
        "--uri", default="wss://localhost:9009/v1/realtime/transcriptions"
    )
    parser.add_argument("--audio", default="./data/vad_example.wav")

    args = parser.parse_args()

    asyncio.run(realtime_transcription(args.uri, args.audio))
