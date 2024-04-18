from voyager import Voyager
from api_keys import openai_api_key
from api_keys import azure_login

model = 'gpt-3.5-turbo'  # 'gpt-4'

voyager = Voyager(
    azure_login=azure_login,
    openai_api_key=openai_api_key,
    action_agent_model_name=model,
    curriculum_agent_model_name=model,
    critic_agent_model_name=model,
    resume=True,
)

# start lifelong learning
voyager.learn()
