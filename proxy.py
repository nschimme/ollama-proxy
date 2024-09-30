import os
import asyncio
from aiohttp import ClientSession, ClientResponseError
from aiohttp.web import Response, StreamResponse, run_app, Application
import json
import sys

# Replace the hardcoded target URL with an environment variable
TARGET_URL = os.getenv('TARGET_URL', 'http://192.168.0.200:11434')

MODEL_SWAP = {
    'codestral': 'codestral:latest',
    'phi3': 'phi3:14b-medium-4k-instruct-q4_K_M',
    'llama3': 'llama3:8b-instruct-q8_0',
    'llama3:8b': 'llama3:8b-instruct-q8_0',
    'codeqwen:code': 'codeqwen:7b-code-v1.5-q8_0',
    'starcoder2': 'starcoder2:15b'
}

async def handle_request(request):
    try:
        method = request.method
        path = request.path_qs
        headers = {key: value for key, value in request.headers.items()}

        if request.can_read_body:
            post_data = await request.read()
        else:
            post_data = None

        if post_data:
            try:
                json_data = json.loads(post_data)
                if "model" in json_data:
                    swap_key = json_data["model"]
                    print(f"json model: {swap_key}")
                    if swap_key in MODEL_SWAP:
                        print("replacing {} with {}".format(swap_key, MODEL_SWAP[swap_key]))
                        json_data["model"] = MODEL_SWAP[swap_key]
                        post_data = json.dumps(json_data).encode('utf-8')
                        headers['Content-Length'] = str(len(post_data))
            except json.JSONDecodeError:
                return Response(status=400, text="Bad Request: Invalid JSON")

        async with ClientSession() as session:
            async with session.request(method, TARGET_URL + path, headers=headers, data=post_data) as response:
                stream_response = StreamResponse(status=response.status, reason=response.reason)
                for key, value in response.headers.items():
                    if key.lower() != 'transfer-encoding':
                        stream_response.headers[key] = value
                await stream_response.prepare(request)

                async for chunk in response.content.iter_any():
                    await stream_response.write(chunk)
                await stream_response.write_eof()

                return stream_response

    except ClientResponseError as e:
        return Response(status=e.status, text=str(e))
    except Exception as e:
        return Response(status=500, text=str(e))

async def create_app():
    app = Application()
    app.router.add_route('*', '/{path_info:.*}', handle_request)  # Match all routes
    return app

if __name__ == '__main__':
    app = create_app()
    run_app(app, host='0.0.0.0', port=11434)

