from django import template

register = template.Library()

# CUSTOM FILTERS FOR TEMPLATES

# Iterate over two lists concurrently
@register.filter(name='zip')
def zip_lists(a, b):
  return zip(a, b)
