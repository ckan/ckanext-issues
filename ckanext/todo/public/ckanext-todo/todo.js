// CKAN Todo Extension

var CKANEXT = CKANEXT || {};

CKANEXT.TODO = {
    init:function(packageName, userID){
        this.packageName = packageName;
        this.userID = userID;
        this.todoCount = 0;
        this.showTodo();
        // autocomplete
        $('.autocomplete-todo-category').autocomplete({source:'/api/2/todo/autocomplete'});
    },

    // show the todo count
    showTodoCount:function(){
        var html = '<a id="package-todo-count" class="button pcb" ' +
            'href="#todo"><span>Nothing Todo</span></a>';
        if(this.todoCount != 0){
            html = html.replace('Nothing', this.todoCount);
        }
        $('a#package-todo-count').replaceWith(html);
    },

    // create and return the HTML code for 1 todo item
    todoItem:function(data){
        var html = '<table id="todo-item-' + data.id + '" ';
        html += 'class="todo-item"><tbody>';
        html += '<tr>';
        html += '<td class="todo-list-title">Category</td>';
        html += '<td>' + data.category + '</td>';
        html += '</tr>';
        html += '<tr>';
        html += '<td class="todo-list-title">Description</td>';
        html += '<td>' + data.description + '</td>';
        html += '</tr>';
        html += '<tr>';
        html += '<td class="todo-list-title">Creator</td>';
        html += '<td>' + data.creator + '</td>';
        html += '</tr>';
        html += '<tr>';
        html += '<td class="todo-list-title">Creation Date</td>';
        html += '<td>' + data.created + '</td>';
        html += '</tr>';

        // display the resolve button if user is logged in
        if(CKANEXT.TODO.userID != ''){
            html += '<tr>';
            html += '<td class="todo-list-title"></td>';
            html += '<td><a id="resolve-' + data.id + '" ';
            html += 'class="resolve-button" >';
            html += '<span>Mark as resolved</span></a></td>';
            html += '</tr>';
        }

        html += '</tbody></table>';
        
        return html;
    },

    // show the number of todo items for this package, and display the 
    // 'Add a todo' button/form
    showTodo:function(){
        var todoData = "resolved=0&package=" + this.packageName;

        var todoSuccess = function(data){
            // set the package todo count and display it
            CKANEXT.TODO.todoCount = data.length;
            CKANEXT.TODO.showTodoCount();

            // Show a table for each todo item listing the todo category, description,
            // creator and creation date
            if(data.length != 0){
                var todoHtml = '<div id="todo-list">';
                for(var i in data){
                    todoHtml += CKANEXT.TODO.todoItem(data[i]);
                }
                todoHtml += '</div>';
                $('div#todo-list').replaceWith(todoHtml);
                $('.resolve-button').button();
            }
            else{
                var todoHtml = '<div id="todo-list">Nothing todo for this package.</div>';
                $('div#todo-list').replaceWith(todoHtml);
            }

            // if user is not logged in, show a disabled button prompting them to login
            if(CKANEXT.TODO.userID == ''){
                $('#todo-button').button( {disabled: true, label: "Login to add todo items" });
            }
            else{
                // show the 'Add a todo button'
                $('#todo-button').button({ label: "Add a todo" });
                // add a click handler to the 'Add a todo' button
                $('#todo-button').click(CKANEXT.TODO.addTodo);
                // add a click handler to the form submit button
                $('#todo-add-button').button({ label: "Add" });
                $('#todo-add-button').click(CKANEXT.TODO.addNewTodo);
                // add click handler for resolve buttons
                $('.resolve-button').click(CKANEXT.TODO.resolve);
            }
        };

        var todoError = function(error){
            var errorHtml = '<div id="todo-error">Error: ' +
                'Could not get Todo items for this package, please try again' +
                ' later (Error STATUS).</div>';
            errorHtml = errorHtml.replace('STATUS', error.status);
            $('div#todo-error').replaceWith(errorHtml);
        };

        $.ajax({method: 'GET',
                url: '/api/2/todo',
                dataType: 'json',
                data: todoData,
                success: todoSuccess,
                error: todoError
        }); 
    },

    // callback handler for the 'add a todo' button clicked
    // disables the button and displays the form
    addTodo:function(){
        $('#todo-add').show(500);
        $('#todo-button').button("option", "disabled", true);
    },

    // callback handler for the 'add' button clicked (submit new todo item)
    addNewTodo:function(){
        var category = $('input[name="category_name"]').val();
        var description = $('textarea[name="description"]').val();

        data = {creator: CKANEXT.TODO.userID,
                package_name: CKANEXT.TODO.packageName,
                category_name: category,
                description: description};

        $.post("/api/2/todo", data,
            // successful
            function(response){
                // briefly disable add button
                $('#todo-add-button').button("option", "disabled", true);

                // remove any existing error message
                $('div#todo-error').empty();
                // update the todo count
                CKANEXT.TODO.todoCount = CKANEXT.TODO.todoCount + 1;
                CKANEXT.TODO.showTodoCount();

                // update the list
                var showNewTodo = function(data){
                    var todoHtml = CKANEXT.TODO.todoItem(data[0]);
                    $('div#todo-list').prepend(todoHtml);
                    // add click handler for resolve button
                    $('#resolve-' + data[0].id).button();
                    $('#resolve-' + data[0].id).click(CKANEXT.TODO.resolve);
                };
                var todoData = "package=" + CKANEXT.TODO.packageName + "&limit=1";

                $.ajax({method: 'GET',
                        url: '/api/2/todo',
                        data: todoData,
                        dataType: 'json',
                        async:   false,
                        success: showNewTodo
                }); 

                // remove the todo form and reenable the add buttons
                $('#todo-add').fadeOut(500);
                $('#todo-button').button("option", "disabled", false);
                $('#todo-add-button').button("option", "disabled", false);
        })
        .error(
            function(error){
                console.log(error.responseText);
                var errorHtml = '<div id="todo-error">Error: ' +
                    JSON.parse(error.responseText).msg + '</div>';
                errorHtml = errorHtml.replace('STATUS', error.status);
                $('div#todo-error').replaceWith(errorHtml);
        });
    },

    // callback handler for resolve buttons
    resolve:function(e){
        // get the todo ID from the button ID
        todo_id = $(e.currentTarget).attr('id').substr("resolve-".length);

        data = {todo_id: todo_id,
                resolver: CKANEXT.TODO.userID};

        $.post("/api/2/todo/resolve", data,
            // successful
            function(response){
                // remove any existing error message
                $('div#todo-error').empty();
                // hide the todo item
                $('table#todo-item-' + todo_id).fadeOut(500);
                // reduce the todo count by 1
                CKANEXT.TODO.todoCount = CKANEXT.TODO.todoCount - 1;
                CKANEXT.TODO.showTodoCount();
        })
        .error(
            function(error){
                var errorHtml = '<div id="todo-error">Error: ' +
                    'Could not resolve the todo item, please try again' +
                    ' later (Error STATUS).</div>';
                errorHtml = errorHtml.replace('STATUS', error.status);
                $('div#todo-error').replaceWith(errorHtml);
        });
    },
};
