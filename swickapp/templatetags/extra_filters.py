from django import template

register = template.Library()

# Allow two lists to be concurrently iterated over in templates
@register.filter(name='zip')
def zip_lists(a, b):
  return zip(a, b)
