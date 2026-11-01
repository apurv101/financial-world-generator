"""tell_story: a narrator saves the detailed story of its part of the world."""

from pydantic import BaseModel, ConfigDict, Field

from worldgen.tools.base import Tool
from worldgen.tools.tree.context import TreeContext


class TellStoryInput(BaseModel):
    model_config = ConfigDict(extra="forbid")

    story: str = Field(
        min_length=1, description="The whole story of your part, in prose with headings."
    )


class TellStory(Tool[TreeContext, TellStoryInput]):
    name = "tell_story"
    description = (
        "Saves the full story of your part of the world: what it is and when, its history before "
        "the first day, the cast, the money (accounts, institutions, relationships, amounts, "
        "schedules, payment methods), dated events and plans, and texture. Your children never "
        "see it: it is your record of your part and the source for the prompts and briefs you "
        "write. Calling it again replaces the earlier story, so always send the whole story."
    )
    input_model = TellStoryInput

    def run(self, ctx: TreeContext, args: TellStoryInput) -> str:
        replaced = ctx.node.story is not None
        ctx.node.story = args.story
        words = len(args.story.split())
        return f"{'Replaced your story' if replaced else 'Saved your story'} ({words} words)."
