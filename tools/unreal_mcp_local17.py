"""Call the discovered native Unreal MCP endpoint over local HTTP.

Fallback for a client session whose bundled Unreal connection is not exposed.
Schemas are obtained from tools/list and describe_toolset before dispatch.
"""
from pathlib import Path
import argparse,json,urllib.request


class UnrealMCP:
    def __init__(self):self.session=None;self.counter=0
    def request(self,method,params=None,notification=False):
        payload={'jsonrpc':'2.0','method':method}
        if not notification:self.counter+=1;payload['id']=self.counter
        if params is not None:payload['params']=params
        headers={'Content-Type':'application/json','Accept':'application/json, text/event-stream','MCP-Protocol-Version':'2025-06-18'}
        if self.session:headers['Mcp-Session-Id']=self.session
        request=urllib.request.Request('http://127.0.0.1:8000/mcp',data=json.dumps(payload).encode(),headers=headers)
        with urllib.request.urlopen(request,timeout=50) as response:
            self.session=response.headers.get('Mcp-Session-Id',self.session)
            if response.status==202:return None
            if 'text/event-stream' in response.headers.get('Content-Type',''):
                while line:=response.readline():
                    if line.startswith(b'data:'):
                        value=json.loads(line[5:])
                        if value.get('id')==payload.get('id'):break
                else:raise RuntimeError('No matching MCP response')
            else:value=json.loads(response.read())
        if 'error' in value:raise RuntimeError(value['error'])
        return value.get('result')
    def initialize(self):
        result=self.request('initialize',{'protocolVersion':'2025-06-18','capabilities':{},'clientInfo':{'name':'HumanReferenceStudy','version':'1.0'}})
        self.request('notifications/initialized',notification=True)
        return result


def main():
    parser=argparse.ArgumentParser();parser.add_argument('request_file');parser.add_argument('output_file');args=parser.parse_args()
    request=json.loads(Path(args.request_file).read_text(encoding='utf-8-sig'));client=UnrealMCP();server=client.initialize()
    result=client.request(request['method'],request.get('params'))
    out=Path(args.output_file);out.parent.mkdir(parents=True,exist_ok=True)
    out.write_text(json.dumps({'server':server,'result':result},indent=2),encoding='utf-8')
    print(json.dumps(result,ensure_ascii=False))


if __name__=='__main__':main()
