---
layout: page
homepage: true
---

# Overview

> Takeoff: your runway to the cloud!

This is Takeoff's documentation page, which provides a high-level overview of what Takeoff is, what is can do, and how you can
use it in your environment. 

Schiphol Takeoff is a deployment orchestration tool that abstract away much of the complexity of tying various cloud services together. 
Takeoff allows developers to focus on actual development work, without having to worry about coordinating a (large) number of cloud 
services to get things up and running across multiple environments. Takeoff itself is a Python package, that comes bundles in a Docker image.
In this way, Takeoff is CI agnostic, assuming your CI provider allows running Docker containers. 

# Principles
To understand better why Takeoff exists, it's important to mention some of the principles that were adhered to while building it:
1. Everything is Python. We chose Python for a number of reasons, but the most important ones are that Python code can easily be tested,
has a lot of SDKs available for interacting with clouds and other external system, is easy to read, and is the lingua franca of data science (the initial target audience)
2. Modularity, modularity, and more modularity. By making the interactions with each external system a separate, decoupled module, we have freed to way
for others to extend Takeoff to fulfill their requirements, without having to rewrite (too much) for every new component.
3. We ain't Ansible, Puppet, or Terraform. The goal of Takeoff was never, and will never, be to deploy infrastructure. Tools like Terraform are much better at this than
we could ever hope to be. Takeoff is specifically aimed at your CI process when working with multiple cloud components, and having to orchestrate these components to 
work nicely together to deliver an awesome product.

# Getting started
To get started quickly, have look [here](getting-started) to read more on how to setup Takeoff in your project.

# Contributing
To get started with contributing to Takeoff read the [developers guide](contributing-takeoff).

To get started with contributing to documentation for Takeoff read the [documentation guide](contributing-takeoff-docs).
