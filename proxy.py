import os
import asyncio
from aiohttp import ClientSession, ClientResponseError
from aiohttp.web import Response, StreamResponse, run_app, Application
import json
import sys

# Replace the hardcoded target URL with an environment variable
TARGET_URL = os.getenv('TARGET_URL', 'http://192.168.0.200:11434')

MODEL_SWAP = {
    'codestral': 'codestral:22b-v0.1-q4_K_M',
    'phi3': 'phi3:14b-medium-4k-instruct-q4_K_M',
    'llama3': 'llama3:8b-instruct-q8_0',
    'llama3:8b': 'llama3:8b-instruct-q8_0',
    'codeqwen:code': 'codeqwen:7b-code-v1.5-q8_0',
    'starcoder2': 'starcoder2:15b',
    'starcoder2:3b': 'starcoder2:15b'
}

async def handle_request(request):
    try:
        method = request.method
        path = request.path_qs
        headers = {key: value for key, value in request.headers.items() if key.lower() not in {'content-length'}}
        if request.can_read_body:
            post_data = await request.read()
        else:
            post_data = None
        if post_data:
            try:
                json_data = json.loads(post_data)
                if "model" in json_data and json_data["model"] in MODEL_SWAP:
                    print("replacing {} with {}".format(json_data["model"], MODEL_SWAP[json_data["model"]]))
                    json_data["model"] = MODEL_SWAP[json_data["model"]]
                del_keys = ["raw", "options","keep_alive"]
                for dkey in del_keys:
                    if dkey in json_data:
                        del json_data[dkey]
                post_data = json.dumps(json_data).encode('utf-8')
            except json.JSONDecodeError:
                return Response(status=400, text="Bad Request: Invalid JSON")
            print(post_data)
        async with ClientSession() as session:
            # print(method, " ", TARGET_URL, path)
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

async def list_models():
    async with ClientSession() as session:
        async with session.request('GET', TARGET_URL + '/api/tags') as response:
            return await response.json()

def print_table(data):
    col_widths = [max(len(str(row[i])) for row in data) + 2 for i in range(len(data[0]))]
    print(''.join(str(item).ljust(col_widths[i]) for i, item in enumerate(data[0])))
    print('-' * (sum(col_widths) + 1))
    for row in data[1:]:
        print(''.join(str(item).ljust(col_widths[i]) for i, item in enumerate(row)))

async def create_app():
    app = Application()
    app.router.add_route('*', '/{path_info:.*}', handle_request)  # Match all routes
    return app

if __name__ == '__main__':
    # print ollama models available
    available_models = set()
    models = asyncio.run(list_models())
    if 'models' in models:
        m = [["Name", "Size"]]
        for model in models['models']:
            size_str = "{:.2f} GB".format(float(model['size'])/1073741824.0)
            m.append([model['model'],size_str])
            available_models.add(model['model'])
        print_table(m)
    # check and warn if replacement is to a non-existent model
    for key, value in MODEL_SWAP.items():
        if value not in available_models:
            print(f"WARNING: MODEL_SWAP contains a non-existent model: {key} -> {value}")
    
    # run aiohttp proxy
    app = create_app()
    run_app(app, host='0.0.0.0', port=11434)

