"""
CKAN Todo Extension
"""

HEAD_CODE = """
<link rel="stylesheet" href="/ckanext-todo/css/main.css" 
      type="text/css" media="screen" /> 
<link rel="stylesheet" href="/ckanext-todo/css/buttons.css" 
      type="text/css" media="screen" /> 
"""

BODY_CODE = """
<script type="text/javascript" src="/ckanext-todo/jquery-1.5.2.min.js"></script>
<script type="text/javascript" src="/ckanext-todo/scroll.js"></script>
<script type="text/javascript" src="/ckanext-todo/todo.js"></script>
<script type="text/javascript">
    jQuery.noConflict();
    jQuery('document').ready(function($){
        CKANEXT.TODO.init('%(package)s', '%(user_id)s');
    });
</script>
"""

TODO_CODE = """
<div id="todo" class="subsection">
    <h3>Todo</h3>
    <a id="todo-button"></a>

    <div id="todo-add">
        <form name="todo-add-form" method="post">
            <div>
                <label for="category_name">Category</label>
                <input name="category_name" class="autocomplete-todo-category" type="text" />
            </div>
            <div>
                <label for="description">Description</label>
                <textarea name="description"></textarea>
            </div>
            <div>
                <a id="todo-add-button"></a>
            </div>
        </form>
    </div>

    <div id="todo-error"></div>
    <div id="todo-list"></div>
</div>
"""

MENU_CODE = """
%(href)s
"""
