$(function() {
    hljs.initHighlightingOnLoad();
    var markdown = new showdown.Converter();
    markdown.setOption('ghCodeBlocks', true);

    var scope = Object();

    var load_token_info = function() {
        $.ajax({
            url: '/token/me',
            success: function(data) {
                scope.run = data.run;
                scope.name = data.name;
                $('#user_name').html(data.name);
                $('#run_name').html(data.run);
            },
            error: function(r) {
                $('#user_name').html('ERROR');
                $('#run_name').html('ERROR');
            }
        });

    };

    var load_test_cases = function() {
        $.ajax({
            url: '/record',
            success: function(data) {
                $('#test_list').html('');
                $.each(data.entries, function(index, category) {
                    var ul = $('<ul class="test_case_list"></ul>');
                    $('#test_list')
                        .append('<h2>' + category.name + '</h2>')
                        .append(ul);
                    $.each(category.entries, function(index, testcase) {
                        var li = $('<li class="test_case_item"></li>');
                        var state = {
                            0: 'not_run',
                            1: 'passed',
                            2: 'failed',
                            3: 'blocked',
                            4: 'skipped',
                        }[testcase.state];
                        var assignee = testcase.assignee || 'unassigned';
                        var unassigned = assignee === 'unassigned' ? ' unassigned' : '';
                        $(li)
                            .append('<span class="state ' + state + '">' + state + '</span>')
                            .append('<span class="test_name">' + testcase.test_name + '</span>')
                            .append('<span class="assignee' + unassigned + '">' + assignee + '</span>');
                        $(ul)
                            .append(li);
                        $(li)
                            .click(function(e) {
                                scope.category = category.name;
                                scope.test_name = testcase.test_name;
                                $('#content_header').html(category.name + ' / ' + testcase.test_name); 
                                $.ajax({
                                    url: testcase.url,
                                    success: function(data) {
                                        $('#content_area').html(markdown.makeHtml(data));
                                    },
                                    error: function(data) {
                                        $('#content_area').html(data);
                                    },
                                })
                            });
                    });
                });
            },
            error: function(data) {
                $('#test_list').html('<p class="error">Failed to load test cases</p>');
            },
        });
    };

    $('#sync_records_button')
        .button()
        .click(function() {
            $('#test_list').html('Syncing test cases...');
            $.ajax({
                url: '/record/sync',
                method: 'POST',
                success: function(data) {
                    load_test_cases();
                },
                error: function(data) {
                    $('#test_list').html('Syncing test cases failed.');
                },
            });
        });

    $('#pass_button')
        .button()
        .click(function() {
            $.ajax({
                url: '/record/op/' + scope.category + '/' + scope.test_name + '/passed',
                method: 'PUT',
                success: function(data) {
                    load_test_cases();
                },
                error: function(data) {
                    $('#test_list').html('Passing failed.');
                },
            });
        });

    $('#fail_button')
        .button()
        .click(function() {
            $.ajax({
                url: '/record/op/' + scope.category + '/' + scope.test_name + '/failed',
                method: 'PUT',
                success: function(data) {
                    load_test_cases();
                },
                error: function(data) {
                    $('#test_list').html('Failing failed.');
                },
            });
        });

    $('#block_button')
        .button()
        .click(function() {
            $.ajax({
                url: '/record/op/' + scope.category + '/' + scope.test_name + '/blocked',
                method: 'PUT',
                success: function(data) {
                    load_test_cases();
                },
                error: function(data) {
                    $('#test_list').html('Blocking failed.');
                },
            });
        });

    $('#skip_button')
        .button()
        .click(function() {
            $.ajax({
                url: '/record/op/' + scope.category + '/' + scope.test_name + '/skipped',
                method: 'PUT',
                success: function(data) {
                    load_test_cases();
                },
                error: function(data) {
                    $('#test_list').html('Skipping failed.');
                },
            });
        });

    $('#reset_button')
        .button()
        .click(function() {
            $.ajax({
                url: '/record/op/' + scope.category + '/' + scope.test_name + '/not_run',
                method: 'PUT',
                success: function(data) {
                    load_test_cases();
                },
                error: function(data) {
                    $('#test_list').html('Resetting failed.');
                },
            });
        });

    load_token_info();
    load_test_cases();
});
