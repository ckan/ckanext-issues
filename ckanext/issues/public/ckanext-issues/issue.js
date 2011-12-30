// CKAN Todo Extension

var CKANEXT = CKANEXT || {};

CKANEXT.ISSUES = {
    init:function(packageName, userID){
        this.packageName = packageName;
        this.userID = userID;
        this.issueCount = 0;
        this.showTodo();
        // autocomplete
        $('.autocomplete-issue-category').autocomplete({source:'/api/2/issue/autocomplete'});
    },

    // show the issue count
    showTodoCount:function(){
        var html = '<a id="package-issue-count" class="button pcb" ' +
            'href="#issue"><span>Nothing Todo</span></a>';
        if(this.issueCount != 0){
            html = html.replace('Nothing', this.issueCount);
        }
        $('a#package-issue-count').replaceWith(html);
    },

    // create and return the HTML code for 1 issue item
    issueItem:function(data){
        var html = '<table id="issue-item-' + data.id + '" ';
        html += 'class="issue-item"><tbody>';
        html += '<tr>';
        html += '<td class="issue-list-title">Category</td>';
        html += '<td>' + data.category + '</td>';
        html += '</tr>';
        html += '<tr>';
        html += '<td class="issue-list-title">Description</td>';
        html += '<td>' + data.description + '</td>';
        html += '</tr>';
        html += '<tr>';
        html += '<td class="issue-list-title">Creator</td>';
        html += '<td>' + data.creator + '</td>';
        html += '</tr>';
        html += '<tr>';
        html += '<td class="issue-list-title">Creation Date</td>';
        html += '<td>' + data.created + '</td>';
        html += '</tr>';

        // display the resolve button if user is logged in
        if(CKANEXT.ISSUES.userID != ''){
            html += '<tr>';
            html += '<td class="issue-list-title"></td>';
            html += '<td><a id="resolve-' + data.id + '" ';
            html += 'class="resolve-button" >';
            html += '<span>Mark as resolved</span></a></td>';
            html += '</tr>';
        }

        html += '</tbody></table>';
        
        return html;
    },

    // show the number of issue items for this package, and display the 
    // 'Add a issue' button/form
    showTodo:function(){
        var issueData = "resolved=0&package=" + this.packageName;

        var issueSuccess = function(data){
            // set the package issue count and display it
            CKANEXT.ISSUES.issueCount = data.length;
            CKANEXT.ISSUES.showTodoCount();

            // Show a table for each issue item listing the issue category, description,
            // creator and creation date
            if(data.length != 0){
                var issueHtml = '<div id="issue-list">';
                for(var i in data){
                    issueHtml += CKANEXT.ISSUES.issueItem(data[i]);
                }
                issueHtml += '</div>';
                $('div#issue-list').replaceWith(issueHtml);
                $('.resolve-button').button();
            }
            else{
                var issueHtml = '<div id="issue-list">Nothing issue for this package.</div>';
                $('div#issue-list').replaceWith(issueHtml);
            }

            // if user is not logged in, show a disabled button prompting them to login
            if(CKANEXT.ISSUES.userID == ''){
                $('#issue-button').button( {disabled: true, label: "Login to add issue items" });
            }
            else{
                // show the 'Add a issue button'
                $('#issue-button').button({ label: "Add a issue" });
                // add a click handler to the 'Add a issue' button
                $('#issue-button').click(CKANEXT.ISSUES.addTodo);
                // add a click handler to the form submit button
                $('#issue-add-button').button({ label: "Add" });
                $('#issue-add-button').click(CKANEXT.ISSUES.addNewTodo);
                // add click handler for resolve buttons
                $('.resolve-button').click(CKANEXT.ISSUES.resolve);
            }
        };

        var issueError = function(error){
            var errorHtml = '<div id="issue-error">Error: ' +
                'Could not get Todo items for this package, please try again' +
                ' later (Error STATUS).</div>';
            errorHtml = errorHtml.replace('STATUS', error.status);
            $('div#issue-error').replaceWith(errorHtml);
        };

        $.ajax({method: 'GET',
                url: '/api/2/issue',
                dataType: 'json',
                data: issueData,
                success: issueSuccess,
                error: issueError
        }); 
    },

    // callback handler for the 'add a issue' button clicked
    // disables the button and displays the form
    addTodo:function(){
        $('#issue-add').show(500);
        $('#issue-button').button("option", "disabled", true);
    },

    // callback handler for the 'add' button clicked (submit new issue item)
    addNewTodo:function(){
        var category = $('input[name="category_name"]').val();
        var description = $('textarea[name="description"]').val();

        data = {creator: CKANEXT.ISSUES.userID,
                package_name: CKANEXT.ISSUES.packageName,
                category_name: category,
                description: description};

        $.post("/api/2/issue", data,
            // successful
            function(response){
                // briefly disable add button
                $('#issue-add-button').button("option", "disabled", true);

                // remove any existing error message
                $('div#issue-error').empty();
                // update the issue count
                CKANEXT.ISSUES.issueCount = CKANEXT.ISSUES.issueCount + 1;
                CKANEXT.ISSUES.showTodoCount();

                // update the list
                var showNewTodo = function(data){
                    var issueHtml = CKANEXT.ISSUES.issueItem(data[0]);
                    $('div#issue-list').prepend(issueHtml);
                    // add click handler for resolve button
                    $('#resolve-' + data[0].id).button();
                    $('#resolve-' + data[0].id).click(CKANEXT.ISSUES.resolve);
                };
                var issueData = "package=" + CKANEXT.ISSUES.packageName + "&limit=1";

                $.ajax({method: 'GET',
                        url: '/api/2/issue',
                        data: issueData,
                        dataType: 'json',
                        async:   false,
                        success: showNewTodo
                }); 

                // remove the issue form and reenable the add buttons
                $('#issue-add').fadeOut(500);
                $('#issue-button').button("option", "disabled", false);
                $('#issue-add-button').button("option", "disabled", false);
        })
        .error(
            function(error){
                console.log(error.responseText);
                var errorHtml = '<div id="issue-error">Error: ' +
                    JSON.parse(error.responseText).msg + '</div>';
                errorHtml = errorHtml.replace('STATUS', error.status);
                $('div#issue-error').replaceWith(errorHtml);
        });
    },

    // callback handler for resolve buttons
    resolve:function(e){
        // get the issue ID from the button ID
        issue_id = $(e.currentTarget).attr('id').substr("resolve-".length);

        data = {issue_id: issue_id,
                resolver: CKANEXT.ISSUES.userID};

        $.post("/api/2/issue/resolve", data,
            // successful
            function(response){
                // remove any existing error message
                $('div#issue-error').empty();
                // hide the issue item
                $('table#issue-item-' + issue_id).fadeOut(500);
                // reduce the issue count by 1
                CKANEXT.ISSUES.issueCount = CKANEXT.ISSUES.issueCount - 1;
                CKANEXT.ISSUES.showTodoCount();
        })
        .error(
            function(error){
                var errorHtml = '<div id="issue-error">Error: ' +
                    'Could not resolve the issue item, please try again' +
                    ' later (Error STATUS).</div>';
                errorHtml = errorHtml.replace('STATUS', error.status);
                $('div#issue-error').replaceWith(errorHtml);
        });
    },
};
