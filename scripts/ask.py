"""Ask the deployed agent a question from the command line.

Usage: python scripts/ask.py "How many days of annual leave do I get?"

Needs two environment variables:
  ASK_URL      the AskUrl output of the stack
  ASK_API_KEY  the value of the API key
"""

import json
import os
import sys
import urllib.error
import urllib.request


def ask(url, api_key, question):
    request = urllib.request.Request(
        url,
        data=json.dumps({"question": question}).encode("utf-8"),
        headers={"Content-Type": "application/json", "x-api-key": api_key},
        method="POST",
    )
    try:
        with urllib.request.urlopen(request, timeout=40) as response:
            return json.loads(response.read())
    except urllib.error.HTTPError as error:
        sys.exit(f"Request failed with status {error.code}: {error.read().decode()}")


def main():
    url = os.environ.get("ASK_URL")
    api_key = os.environ.get("ASK_API_KEY")
    if not url or not api_key:
        sys.exit("Set ASK_URL and ASK_API_KEY first. See the README.")
    if len(sys.argv) < 2:
        sys.exit('Usage: python scripts/ask.py "your question"')

    result = ask(url, api_key, " ".join(sys.argv[1:]))
    print(result["answer"])
    if result["sources"]:
        print("\nSources: " + ", ".join(result["sources"]))


if __name__ == "__main__":
    main()
