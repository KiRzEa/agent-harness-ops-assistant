import asyncio
import json
from collections.abc import Callable

import typer

from src.bootstrap import create_run_service
from src.core.config import get_settings
from src.core.logging import configure_logging
from src.services.run_service import RunService

cli = typer.Typer(add_completion=False, help="Ops assistant agent harness")


async def run_objective(
    service: RunService,
    objective: str,
    ask_approval: Callable[[dict], bool],
    show: Callable[[str], None] = print,
) -> dict:
    run = await service.start_run(objective)
    show(f"Run {run['run_id']} started")
    while run["status"] == "AWAITING_APPROVAL":
        approved = ask_approval(run["pending_approval"])
        run = await (service.approve(run["run_id"]) if approved else service.reject(run["run_id"]))
    show(f"Status: {run['status']}")
    if run["final_answer"]:
        show(f"Answer: {run['final_answer']}")
    if run["error"]:
        show(f"Error: {run['error']['code']} - {run['error']['message']}")
    return run


def ask_operator(pending_approval: dict) -> bool:
    typer.echo("The assistant wants to create an incident:")
    typer.echo(json.dumps(pending_approval["args"], indent=2))
    return typer.confirm("Approve?")


@cli.callback()
def main_callback() -> None:
    pass


@cli.command()
def run(objective: str, show_trace: bool = typer.Option(False, "--trace")) -> None:
    """Run the assistant on an objective, prompting before any incident is created."""

    async def main() -> None:
        configure_logging(level=40)
        async with create_run_service(get_settings()) as service:
            finished = await run_objective(service, objective, ask_operator, typer.echo)
            if show_trace:
                for event in await service.get_trace(finished["run_id"]):
                    typer.echo(f"{event['seq']:>3} {event['type']:<20} {event['payload']}")

    asyncio.run(main())


if __name__ == "__main__":
    cli()
