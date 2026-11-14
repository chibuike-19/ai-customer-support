"""Railway infrastructure as code for this repository (replaces railway.json).

Preview with `railway config plan`, apply with `railway config apply`.
Railway does not read this file on deploy: a git push deploys the code only.
"""

from railway_sdk import define_railway, github, project, service

# This repository manages only its own resources in the environment.
PARTIAL = "ai-customer-support"


@define_railway
def main(ctx=None):
    app = service(
        "ai-customer-support",
        source=github("chibuike-19/ai-customer-support", branch="main"),
        build={"builder": "DOCKERFILE", "dockerfilePath": "Dockerfile"},
        healthcheck="/health",
        healthcheckTimeout=120,
        # Exactly one replica, in EU West (closest to Supabase): each replica runs a Gmail poller.
        replicas={"europe-west4-drams3a": 1},
        deploy={
            # The poller must run all the time, so never sleep when the dashboard is idle.
            "sleepApplication": False,
            "restartPolicyType": "ON_FAILURE",
            "restartPolicyMaxRetries": 10,
            # Stop the old deploy as the new one starts, so two pollers never run at once.
            "overlapSeconds": 0,
            # Time to finish the email in progress before the old deploy is stopped.
            "drainingSeconds": 30,
        },
    )
    # Variables (secrets) stay managed in the Railway dashboard, not in this file.
    return project("compassionate-tenderness", variables={"managed": False}, resources=[app])
