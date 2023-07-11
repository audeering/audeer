{{ objname | escape | underline}}

.. currentmodule:: {{ module }}

.. autoclass:: {{ objname }}

{% block methods %}
{%- for item in (all_methods + attributes)|sort %}
    {%- if not item.startswith('_') or item in ['__call__', '__eq__', '__lt__', '__le__', '__gt__', '__ge__', '__repr__', '__str__'] %}
        {%- if item in all_methods %}
{{ (item + '()') | escape | underline(line='-') }}
.. automethod:: {{ name }}.{{ item }}
        {%- elif item in attributes %}
{{ item | escape | underline(line='-') }}
.. autoattribute:: {{ name }}.{{ item }}
        {%- endif %}
    {% endif %}
{%- endfor %}
{% endblock %}
