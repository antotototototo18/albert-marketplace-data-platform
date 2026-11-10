{% macro finops_query_comment(node) -%}
  {% set component = 'transform' %}
  {% if node is not none %}
    {% if node.resource_type == 'test' %}
      {% set component = 'quality' %}
    {% else %}
      {% set component = node.config.get('schema') or 'transform' %}
    {% endif %}
  {% endif %}
  {{ return(tojson({
    'team': 'group6',
    'environment': 'course',
    'pipeline': 'marketplace',
    'component': component
  })) }}
{%- endmacro %}
