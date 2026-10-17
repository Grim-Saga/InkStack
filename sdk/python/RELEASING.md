# Python package artifacts

InkStack distributes application artifacts through
[GitHub Releases](https://github.com/Grim-Saga/InkStack/releases), not PyPI.
The `rust-v*` workflow retains platform runtime wheel construction and uploads
the wheels as GitHub Release assets. It does not publish packages to a registry.

The Python SDK implementation, package builders, reusable build workflows, and
tests remain available for local development and CI. No PyPI ownership or
trusted-publisher configuration is assumed. Any future registry distribution
requires a separate ownership and compatibility decision.
