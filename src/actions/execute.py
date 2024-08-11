from typing import Any
from . import base

class ExecutionAction(base.AbstractAction):

    """
    An execution engine using Gorilla LLM. This class should be provided with 
    a query regarding some AWS infra. Could be any of CRUD options. Regardless,
    should be capable of taking the query, converting it into an api call, and 
    returning the response as a json to the user.
    """

    def __init__(self) -> None:
        super().__init__()

    def call_goex(self, prompt: str) -> str:
        """
        Call Goex engine to generate output back to user.
        """
        return ""

    def clean_goex_response(self, response: str, original_query: str) -> str:
        """
        Provided with the response form a goex fn, responds with a 
        user friendly, cleaned up response.
        """
        return ""

    def trigger_action(self, input: str) -> Any:
        """
        Entry point to trigger an execution. The input should be the query representing 
        the api call to make
        """

        # 1. call goex engine
        response = self.call_goex(input)

        # 2. cleanup response for user.
        cleaned_response = self.clean_goex_response(response, input)        

        # 3. ret response to user.
        return cleaned_response

    def clean_input(self, input: str) -> str:
        """
        Overriding parent fn to take an input from the user,
        then generate a new prompt that specifically is focused
        towards READING some data from aws.
        
        This function should be only used as a context provider to then 
        pass into trigger_action. Not something the user will see.
        """

        return ""
