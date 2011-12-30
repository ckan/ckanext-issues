"""
CKAN Issue Extension
"""

HEAD_CODE = """
<link rel="stylesheet" href="/ckanext-issues/css/main.css" 
      type="text/css" media="screen" /> 
<link rel="stylesheet" href="/ckanext-issues/css/buttons.css" 
      type="text/css" media="screen" /> 
"""

BODY_CODE = """
<script type="text/javascript" src="/ckanext-issues/jquery-1.5.2.min.js"></script>
<script type="text/javascript" src="/ckanext-issues/scroll.js"></script>
<script type="text/javascript" src="/ckanext-issues/issue.js"></script>
<script type="text/javascript">
    jQuery.noConflict();
    jQuery('document').ready(function($){
        CKANEXT.ISSUES.init('%(package)s', '%(user_id)s');
    });
</script>
"""

ISSUE_CODE = """
<div id="issue" class="subsection">
    <h3>Issue</h3>
    <a id="issue-button"></a>

    <div id="issue-add">
        <form name="issue-add-form" method="post">
            <div>
                <label for="category_name">Category</label>
                <input name="category_name" class="autocomplete-issue-category" type="text" />
            </div>
            <div>
                <label for="description">Description</label>
                <textarea name="description"></textarea>
            </div>
            <div>
                <a id="issue-add-button"></a>
            </div>
        </form>
    </div>

    <div id="issue-error"></div>
    <div id="issue-list"></div>
</div>
"""

MENU_CODE = """
%(href)s
"""
