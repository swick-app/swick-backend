from django import template

register = template.Library()

# CUSTOM FILTERS FOR TEMPLATES

# Iterate over two lists concurrently
@register.filter(name='zip')
def zip_lists(a, b):
  return zip(a, b)

# Get class name of object
@register.filter(name='get_class')
def get_class(value):
  return value.__class__.__name__
