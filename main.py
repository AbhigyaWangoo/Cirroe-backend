from include.llm.gpt import GPTClient

sysp="You are a cloud engineer. The user will be providing you with a description of an AWS infrastructure that they would like to setup. Your job is to extract an AWS CloudFormation Template from the provided query. You must return your responses in JSON format."
q="Setup a load test that tests nginx servers in around 5 c5.4xlarge instances. I should be able to see their latency and bandwidth upper limits."

print(GPTClient().query(q, sys_prompt=sysp, is_json=True))