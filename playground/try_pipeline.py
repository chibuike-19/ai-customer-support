import sys
from pathlib import Path

sys.path.append(str(Path(__file__).resolve().parents[1]))

from app.ai.decide import decide_sync

question = "Hi, how many Wellwoman Max tablets should I take a day? Thanks, Ada"
decision = decide_sync(question)
print(decision.model_dump_json(indent=2))
