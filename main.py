import argparse
from dotenv import load_dotenv
load_dotenv()
from agent import FatigueAgent

if __name__ == "__main__":
    p = argparse.ArgumentParser(description="Fatigue Design Agent")
    p.add_argument("task", nargs="?", help="Task in plain English (omit for interactive mode)")
    p.add_argument("-q", "--quiet", action="store_true", help="Hide reasoning trace")
    a = p.parse_args()
    agent = FatigueAgent(verbose=not a.quiet)
    if a.task:
        print("\n=== FINAL ANSWER ===\n" + agent.run(a.task))
    else:
        while (t := input("\nTask (blank to quit)> ").strip()):
            print("\n=== FINAL ANSWER ===\n" + agent.run(t))
