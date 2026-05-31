import urllib.request
import json
import time
import subprocess
import sys

def run_test():
    # Payload for the damage server
    payload = {
        "genNum": 5,
        "attacker": {
            "name": "Alakazam",
            "options": {
                "nature": "Modest",
                "item": "Life Orb",
                "evs": { "spa": 252 }
            }
        },
        "defender": {
            "name": "Mew",
            "options": {
                "evs": { "hp": 4 }
            }
        },
        "moveName": "Psychic"
    }

    url = 'http://localhost:3000/calculate'
    req = urllib.request.Request(
        url,
        data=json.dumps(payload).encode('utf-8'),
        headers={'Content-Type': 'application/json'},
        method='POST'
    )

    print("Sending calculation request to Express API...")
    try:
        with urllib.request.urlopen(req, timeout=5) as response:
            res_body = response.read().decode('utf-8')
            data = json.loads(res_body)
            print("\n--- Damage Server API Response Success! ---")
            print(f"Description: {data['description']}")
            print(f"Damage Rolls: {data['damageRolls']}")
            print(f"Defender Max HP: {data['defenderMaxHP']}")
            print(f"Min taken: {data['percentages']['minPercent']}")
            print(f"Max taken: {data['percentages']['maxPercent']}")
    except Exception as e:
        print(f"Error making request: {e}")
        sys.exit(1)

if __name__ == '__main__':
    run_test()
