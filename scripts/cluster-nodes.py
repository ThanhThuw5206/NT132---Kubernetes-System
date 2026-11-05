#!/usr/bin/env python3
"""Resolve lab node names by reserved InternalIP, including GCE FQDN names."""
import json
import sys


def resolve(payload):
    result = []
    for ip in ("10.20.0.10", "10.20.0.11", "10.20.0.12"):
        matches = [node["metadata"]["name"] for node in payload["items"]
                   if any(address.get("type") == "InternalIP" and address.get("address") == ip
                          for address in node.get("status", {}).get("addresses", []))]
        if len(matches) != 1:
            raise ValueError(f"Expected exactly one node with InternalIP {ip}; found {len(matches)}")
        result.append(matches[0])
    if len(set(result)) != 3:
        raise ValueError("Expected three distinct nodes")
    return result


if __name__ == "__main__":
    try:
        print("\n".join(resolve(json.load(sys.stdin))))
    except (ValueError, KeyError) as error:
        sys.exit(str(error))
