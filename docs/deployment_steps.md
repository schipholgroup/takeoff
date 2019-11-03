---
layout: page
title: Deployment steps
rank: 3
permalink: deployment-steps
---

{% assign groups = site.deployment-steps | group_by: 'category' | sort: 'name' %}
{% for group in groups %}
# {{ group.name }}
<ul>
    {% for step in group.items %}
        <li>
            <a href="{{ step.url | relative_url }}">{{ step.title }}</a> <br>
            <i> {{ step.summary }} </i>
        </li>
    {% endfor %}
</ul>
{% endfor %}

