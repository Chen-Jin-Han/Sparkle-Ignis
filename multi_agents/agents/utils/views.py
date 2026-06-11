from colorama import Fore, Style
from enum import Enum


class AgentColor(Enum):
    RESEARCHER = Fore.LIGHTBLUE_EX
    EDITOR = Fore.YELLOW
    WRITER = Fore.LIGHTGREEN_EX
    PUBLISHER = Fore.MAGENTA
    REVIEWER = Fore.CYAN
    REVISOR = Fore.LIGHTWHITE_EX
    MASTER = Fore.LIGHTYELLOW_EX


AGENT_DISPLAY_NAMES = {
    "RESEARCHER": "Blaze",
    "EDITOR": "Flare",
    "WRITER": "Kindle",
    "PUBLISHER": "Pyre",
    "REVIEWER": "Cinder",
    "REVISOR": "Forge",
    "MASTER": "Ignis",
}


def print_agent_output(output:str, agent: str="RESEARCHER"):
    color = AgentColor.__members__.get(agent, AgentColor.RESEARCHER).value
    display_name = AGENT_DISPLAY_NAMES.get(agent, agent.title())
    print(f"{color}{display_name}: {output}{Style.RESET_ALL}")
