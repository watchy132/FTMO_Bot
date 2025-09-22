import gpt_bridge as g

print(
    "tool_calls:",
    g.normalize_setups(
        {
            "choices": [
                {
                    "message": {
                        "tool_calls": [
                            {
                                "function": {
                                    "arguments": '{"setups":[{"symbol":"EURUSD","direction":"BUY","entry":1.172,"sl":1.17,"tp":1.175}]}'
                                }
                            }
                        ]
                    }
                }
            ]
        }
    ),
)
print(
    "content:",
    g.normalize_setups(
        {
            "choices": [
                {
                    "message": {
                        "content": '```json\n[{"symbol":"EURUSD","direction":"BUY","entry":1.172,"sl":1.17,"tp":1.175}]\n```'
                    }
                }
            ]
        }
    ),
)
