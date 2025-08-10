#!/usr/bin/env python3
import secrets

def main() -> None:
    print(secrets.token_hex(32))

if __name__ == "__main__":
    main()


