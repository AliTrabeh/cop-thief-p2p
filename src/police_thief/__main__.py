import ssl  # noqa: F401 — must import before httpx/FastMCP to fix Windows OpenSSL DLL ordering

from police_thief.cli import main

if __name__ == "__main__":
    main()
