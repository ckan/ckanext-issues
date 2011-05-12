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
    $('document').ready(function($){
        CKANEXT.TODO.init('%(package_id)s', '%(package_name)s', '%(user_id)s');
    });
</script>
"""

TODO_COUNT_CODE = """
<span id="todo-count">
<a id="package-todo-count"></a>
</span>
"""

TODO_CODE = """
<div id="todo" class="subsection">
    <h3>Todo</h3>
    <ul id="todo-list">
        <li>Nothing todo for this package.</li>
    </ul>
</div>
"""

ERROR_CODE = """
<div id="todo-error"></div>
"""
