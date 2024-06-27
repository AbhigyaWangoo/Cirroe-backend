from src.actions.construct import ConstructCFStackAction

q = "Setup a load test that tests nginx servers in around 5 c5.4xlarge instances. I should be able to see their latency and bandwidth upper limits."

print(ConstructCFStackAction().trigger_action(q))
# print(GPTClient().query(q, sys_prompt=sysp, is_json=True))
