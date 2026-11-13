import sys
from pathlib import Path

import nest_asyncio

sys.path.append(str(Path(__file__).resolve().parents[1]))

nest_asyncio.apply()
from app.ai.decide import decide

question = "Hi, how many Wellwoman Max tablets should I take a day? Thanks, Ada"
decision = decide(question)
print(decision.model_dump_json(indent=2))