---
layout: page
title: Deployment Steps
rank: 2
permalink: deployment-steps
---

{% assign groups = site.deployment-steps | group_by: 'category' | sort: 'name' %}
{% for group in groups %}
# {{ group.name }}
<ul>
    {% for step in group.items %}
        <li>
            <a href="takeoff{{ step.url }}">{{ step.title }}</a> <br>
            <i> {{ step.summary }} </i>
        </li>
    {% endfor %}
</ul>
{% endfor %}

