
function ready_popup(trigger_element_id, formURL, dataURL, tax_categories, tax_percentages, tax_category_index, form_id){
  populate_tax_categories(tax_categories, tax_percentages, tax_category_index);
  //$('#' + trigger_element_id).data('prev', tax_category_index);
  //$('#' + trigger_element_id).prop('selectedIndex', tax_category_index);
  attach_modal_form(trigger_element_id, formURL, dataURL);
  attach_post(form_id)
};

// Attach tax category field to form post event upon submission
function attach_post(form_id){
  $("#".concat(form_id)).submit(function(){
     var select = document.getElementById('tax_categories')
     var value = select.options[select.selectedIndex].value
     var form=document.getElementById(form_id);
     var input = document.createElement('input');
     input.setAttribute('name', 'meal_tax_category');
     input.setAttribute('value', value);
     input.setAttribute('type', "hidden");
     form.appendChild(input);
     return true;
     });
}

// attach bootstrap modal form to trigger on element
function attach_modal_form(trigger_element_id, formURL, dataURL){
  $("#".concat(trigger_element_id)).modalForm({
    formURL: formURL, // url of form to show in popup
    asyncUpdate: true,
    asyncSettings: {
      closeOnSubmit: true,
      successMessage: "n/a",
      dataUrl: dataURL, // url name to retrieve updated elements
      dataElementId: "#tax_categories", // data element to update
      dataKey: "category",
      addModalFormFunction: post_modal_form_actions, // function to run after async completion
    }
  });
}

// Sorts indexes and assigns the idx of selected element
function sort_options_arr(option_value, default_option){
  var select_doc_element = document.getElementById('tax_categories');
  var select_jquery_element = $('#tax_categories');
  var options = $("#tax_categories option", );
  var default_idx = 0;
  var selected_idx_temp = 0;

  options.sort(function(x,y){
    if(x.value.toLowerCase() < y.value.toLowerCase()) return -1;
    if(x.value.toLowerCase() > y.value.toLowerCase()) return 1;
    return 0;
  });

  // Find index of "Default" and selected option in sorted arr
  for(var i = 0; i < options.length; ++i){
    if(options[i].value == "Default"){
      default_idx = i;
    }
  }

  // Shift every element from 0 to default over to insert
  // default in first element
  for(var i = default_idx; i > 0; --i){
    options[i] = options[i - 1];
  }

  // set first option to default after shifting
  options[0] = default_option

  // set selected index to inputed option
  for(var i = 0; i < options.length; ++i){
    if(options[i].value == option_value){
      selected_idx_temp = i;
      break;
    }
  }

  select_jquery_element.empty().append(options);
  select_jquery_element.append($('<option>', {
    value: 'add_tax_category',
    text: 'ADD NEW CATEGORY',
    id: 'add-tax-category-option'
  }));

  select_doc_element.selectedIndex = selected_idx_temp
  select_jquery_element.data('prev', selected_idx_temp)
}

function populate_tax_categories(tax_categories, tax_percentages, tax_category_index){
  var select = $("#tax_categories");

  for(var i = 0; i < tax_categories.length; ++i){
    var name_percent = tax_categories[i].concat(" (", tax_percentages[i], "%)");
    select.append($('<option>', {
        value: tax_categories[i],
        text: name_percent,
    }));
  }

  var default_option = document.getElementById('tax_categories').options[0];

  sort_options_arr(tax_categories[tax_category_index], default_option);
}

function post_modal_form_actions(){
  <!--- TODO: May need to refactor if we want to abstract javascript more --->
  var select = document.getElementById('tax_categories')
  var new_option_value = select.options[select.options.length - 1].value;
  var default_option = select.options[0];

  sort_options_arr(new_option_value, default_option);
}
