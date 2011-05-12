// CKAN Todo Extension

var CKANEXT = CKANEXT || {};

CKANEXT.TODO = {
    init:function(packageID, userID){
        this.packageID = packageID;
        this.userID = userID;
        this.showTodo();
    },

    // show the number of todo items for this package
    showTodo:function(){
        var todoData = "package=" + this.packageID;

        var todoSuccess = function(data){
            // display the package todo count
            var html = '<a id="package-todo-count" class="button pcb" ' +
                'href="#todo"><span>Nothing Todo</span></a>';
            if(data.length != 0){
                html = html.replace('Nothing', data.length);
            }
            $('a#package-todo-count').replaceWith(html);

            // Show a table for each todo item listing the todo category, description,
            // creator and creation date
            if(data.length != 0){
                var todoHtml = '<div id="todo-list">';

                for(var i in data){
                    todoHtml += '<table class="todo-item"><tbody>';
                    todoHtml += '<tr>';
                    todoHtml += '<td class="todo-list-title">Category</td>';
                    todoHtml += '<td>' + data[i].category + '</td>';
                    todoHtml += '</tr>';

                    todoHtml += '<tr>';
                    todoHtml += '<td class="todo-list-title">Description</td>';
                    todoHtml += '<td>' + data[i].description + '</td>';
                    todoHtml += '</tr>';

                    todoHtml += '<tr>';
                    todoHtml += '<td class="todo-list-title">Creator</td>';
                    todoHtml += '<td>' + data[i].creator + '</td>';
                    todoHtml += '</tr>';

                    todoHtml += '<tr>';
                    todoHtml += '<td class="todo-list-title">Creation Date</td>';
                    todoHtml += '<td>' + data[i].created + '</td>';
                    todoHtml += '</tr>';
                    todoHtml += '</tbody></table>';
                }

                todoHtml += '</div>';
                $('div#todo-list').replaceWith(todoHtml);
            }
        };

        var todoError = function(data){
            console.log('error');
        };

        $.ajax({method: 'GET',
                url: '/api/2/todo',
                dataType: 'json',
                data: todoData,
                success: todoSuccess,
                error: todoError
        }); 

        // if user is not logged in, show a disabled button prompting them to login
        if(this.userID == ''){
            var todoButtonHtml = '<a id="todo-button" class="disabled-button pcb">' +
                '<span>Login to add todo items</span></a>';
            $('a#todo-button').replaceWith(todoButtonHtml);
        }
        else{
            var todoButtonHtml = '<a id="todo-button" class="positive-button pcb">' +
                '<span>Add a todo</span></a>';
            $('a#todo-button').replaceWith(todoButtonHtml);
            // add a click handler to display the form
            $('a#todo-button').click(function(){
                $('#todo-add').show(500);
                // $('a#todo-button').hide(500);
            });
        }
    }
};
