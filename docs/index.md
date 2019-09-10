---
layout: page
homepage: true
---

# Overview

> Takeoff is the deployment project that helps your project take-off into the cloud

The project is written in python and follows the normal DAP flow. Each contribution to your git project is deployed into the cloud based on the following criteria:

- DEV: each push to a feature branch. The version for your application will be `your-branch-name`
- ACP: each merge commit to the master branch. The version will be `SNAPSHOT`
- PRD: a github release (using [Semantic versioning](https://semver.org/)). The version will be a three digit, decimal separated number, e.g. `2.1.16`

# Getting started

To get start, have look [here](getting-started) to the first time setup of Takeoff in your project.

# Contributing

To get started with contributing to Takeoff read the [developers guide](contributing-takeoff).

To get started with contributing to documentation for Takeoff read the [documentation guide](contributing-takeoff-docs).
