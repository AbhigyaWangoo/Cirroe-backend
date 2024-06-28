from src.actions.construct import ConstructCFStackAction
from src.actions.edit import EditCFStackAction

q = "Setup a load test that tests nginx servers in around 5 c5.4xlarge instances. I should be able to see their latency and bandwidth upper limits."
q2 = "Actually, instead of using nginx, can you use iperf instead? Don't want to deal with nginx."

construction_action = ConstructCFStackAction()
construction_action.trigger_action(q)

stack = construction_action.stack

edit_action = EditCFStackAction(stack_to_edit=stack)

edit_action.trigger_action(q2)
# print(f"TRGGER ACTION:\n\n{edit_action.trigger_action(q2)}")
