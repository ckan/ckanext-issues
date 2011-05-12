// CKAN Todo Extension

var CKANEXT = CKANEXT || {};

CKANEXT.TODO = {
    init:function(packageID, packageName, userID){
        this.packageID = packageID;
        this.todoCount();
    },

    // show the number of todo items for this package
    todoCount:function(){
        var packageID = this.packageID;

        // $.getJSON('/api/2/todo/package/' + packageID,
        //     function(data){
                // if(data.length == 0){
                    var html = '<a id="package-todo-count" class="button pcb" ' +
                               'href="#todo"><span>Nothing Todo</span></a>';
                // }
                // else{
                //     // if followers, show the count and provide a link to the
                //     // page with a list of package followers
                //     var html = '<a href="HREF" id="package-followers" ' +
                //         'class="button pcb"><span>TEXT</span></a>'
                //     var text = data.length + " Following";
                //     var followersURL = "/package/followers/" + packageName;
                //     html = html.replace('HREF', followersURL);
                //     html = html.replace('TEXT', text);
                // }

                // replace the package followers button
                $('a#package-todo-count').replaceWith(html);
        // });
    }
};
