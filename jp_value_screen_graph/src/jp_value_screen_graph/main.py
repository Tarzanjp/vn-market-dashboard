#!/usr/bin/env python
"""Entry point. See flow.py for the actual graph definition."""

from jp_value_screen_graph.flow import JPValueScreenFlow


def kickoff():
    flow = JPValueScreenFlow()
    flow.kickoff()
    print(f"\nReport: {flow.state.report_path}")


def plot():
    JPValueScreenFlow().plot("jp_value_screen_graph")


def run_with_trigger():
    """Run with a JSON payload, e.g.:
    run_with_trigger '{"sectors": ["銀行", "商社"]}'
    run_with_trigger '{"tickers": ["7203", "6758", "8058"]}'
    """
    import json
    import sys

    if len(sys.argv) < 2:
        raise Exception("No trigger payload provided. Please provide JSON payload as argument.")

    try:
        trigger_payload = json.loads(sys.argv[1])
    except json.JSONDecodeError:
        raise Exception("Invalid JSON payload provided as argument")

    flow = JPValueScreenFlow()
    result = flow.kickoff({"crewai_trigger_payload": trigger_payload})
    print(f"\nReport: {flow.state.report_path}")
    return result


if __name__ == "__main__":
    kickoff()
