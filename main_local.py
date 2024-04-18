from voyager import Voyager
import argparse
from api_keys import openai_api_key

model = 'gpt-3.5-turbo'  # 'gpt-4'

# Argument parser
parser = argparse.ArgumentParser(description='Running Voyager with different sets of parameters.')
parser.add_argument('--port', type=int, default=49172, help='MC port number (default: 49172)')
parser.add_argument('--server_port', type=int, default=3000, help='Server port number (default: 3000)')
args = parser.parse_args()

mc_port = args.port

voyager = Voyager(
    mc_port=mc_port,
    openai_api_key=openai_api_key,
    action_agent_model_name=model,
    curriculum_agent_model_name=model,
    critic_agent_model_name=model,
    resume=True,
)

# start lifelong learning
voyager.learn()
