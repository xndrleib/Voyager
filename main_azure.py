from voyager import Voyager
import argparse
from api_keys import openai_api_key, azure_login

model = 'gpt-3.5-turbo'  # 'gpt-4'

parser = argparse.ArgumentParser(description='Running Voyager with different sets of parameters.')
parser.add_argument('--server_port', type=int, default=3000, help='Server port number (default: 3000)')
parser.add_argument('--resume', type=bool, default=False, help='Resume training')
args = parser.parse_args()

server_port = args.server_port
resume = args.resume

voyager = Voyager(
    azure_login=azure_login,
    server_port=server_port,
    openai_api_key=openai_api_key,
    action_agent_model_name=model,
    curriculum_agent_model_name=model,
    critic_agent_model_name=model,
    resume=resume,
)

# start lifelong learning
voyager.learn()
