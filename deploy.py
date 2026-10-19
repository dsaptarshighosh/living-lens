"""Seed dedicated demo accounts and start the public Render web service."""
import os
from http.server import ThreadingHTTPServer

import server


def required(name: str) -> str:
    value = os.environ.get(name, "").strip()
    if not value:
        raise SystemExit(f"Set the {name} environment variable before starting.")
    return value


def seed_demo_accounts() -> None:
    zoo = required("LIVING_LENS_DEMO_ZOO")
    accounts = (
        ("admin", "Demo Administrator", required("LIVING_LENS_ADMIN_EMAIL"),
         required("LIVING_LENS_ADMIN_PASSWORD")),
        ("zookeeper", "Demo Zookeeper", required("LIVING_LENS_KEEPER_EMAIL"),
         required("LIVING_LENS_KEEPER_PASSWORD")),
    )
    for _, _, email, password in accounts:
        if "@" not in email or len(password) < 16:
            raise SystemExit("Demo account emails must be valid and passwords at least 16 characters.")

    server.initialize()
    with server.db() as connection:
        for role, name, email, password in accounts:
            existing = connection.execute(
                "SELECT role, zoo FROM users WHERE email=?", (email.lower(),)
            ).fetchone()
            if existing:
                if existing["role"] != role or existing["zoo"] != zoo:
                    raise SystemExit(f"The configured demo email conflicts with an existing account: {email}")
                continue
            connection.execute(
                "INSERT INTO users(name,email,password_hash,role,zoo) VALUES(?,?,?,?,?)",
                (name, email.lower(), server.pw_hash(password), role, zoo),
            )


if __name__ == "__main__":
    seed_demo_accounts()
    port = int(os.environ.get("PORT", "10000"))
    print(f"Living Lens is listening on port {port}.")
    ThreadingHTTPServer(("0.0.0.0", port), server.Handler).serve_forever()
