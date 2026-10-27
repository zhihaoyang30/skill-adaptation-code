"""Harbor agents with full skill injection and controlled skill visibility."""
import os
from pathlib import Path

from harbor.agents.installed.claude_code import ClaudeCode
from harbor.agents.installed.openhands_sdk import OpenHandsSDK


class SkillBundle:
    def __init__(self, bundle=None, *args, **kwargs):
        self.bundle = Path(bundle) if bundle else None
        super().__init__(*args, **kwargs)

    async def run(self, instruction, environment, context):
        # These paths are in the fresh benchmark container, never the host.
        clear = "rm -rf /skills; mkdir -p /skills; "
        clear += "for base in /root /home/* /app /workspace; do "
        clear += "for rel in skills .claude/skills .codex/skills .agents/skills .openhands-sdk/skills .opencode/skill .goose/skills .gemini/skills .factory/skills; do "
        clear += 'rm -rf "$base/$rel"; done; done'
        await self.exec_as_root(environment, command=clear)
        if self.bundle:
            await environment.upload_dir(self.bundle, "/skills")
            await self.exec_as_root(environment, command="chmod -R a+rX /skills")
            # Preserve the conventional helper-script paths used by upstream skills.
            await self.exec_as_root(environment, command=(
                "for base in /root /home/* /app /workspace; do "
                'test -d "$base" || continue; '
                "for rel in skills .claude/skills .openhands-sdk/skills; do "
                'mkdir -p "$(dirname "$base/$rel")"; ln -s /skills "$base/$rel"; '
                "done; done"))
            blocks = [f'<skill name="{f.parent.name}">\n{f.read_text()}\n</skill>'
                      for f in sorted(self.bundle.glob("*/SKILL.md"))]
            instruction = "\n\n".join(blocks) + "\n\n" + instruction
        self.skills_dir = "/skills" if self.bundle else None
        return await super().run(instruction, environment, context)


class InjectedOpenHands(SkillBundle, OpenHandsSDK):
    def __init__(self, *args, **kwargs):
        kwargs["load_skills"] = False
        kwargs["extra_env"] = {k: os.environ[k] for k in ("LLM_API_KEY", "LLM_BASE_URL") if k in os.environ}
        super().__init__(*args, **kwargs)


class InjectedClaudeCode(SkillBundle, ClaudeCode):
    def __init__(self, *args, **kwargs):
        kwargs["disallowed_tools"] = "EnterPlanMode ExitPlanMode"
        super().__init__(*args, **kwargs)
