$(function() {
    hljs.initHighlightingOnLoad();
    var markdown = new showdown.Converter();
    markdown.setOption('ghCodeBlocks', true);

    var scope = Object();

    var state_name = {
        0: 'not_run',
        1: 'passed',
        2: 'failed',
        3: 'blocked',
        4: 'skipped',
        5: 'assigned',
    };

    var state_label = {
        passed: 'PASSED',
        failed: 'FAILED',
        blocked: 'BLOCKED',
        skipped: 'SKIPPED',
        not_run: 'NOT RUN',
        assigned: 'ASSIGNED',
    };

    var state_verb = {
        passed: 'PASS',
        failed: 'FAIL',
        blocked: 'BLOCK',
        skipped: 'SKIP',
        not_run: 'RESET',
        assigned: 'PICK UP',
    };

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
        $('#content_header').html('Test Cases');
        $.ajax({
            url: '/record',
            success: function(data) {
                $('#content_area').html('');
                $.each(data.entries, function(index, category) {
                    var ul = $('<ul class="test_case_list"></ul>');
                    $('#content_area')
                        .append('<h2>' + category.name + '</h2>')
                        .append(ul);
                    $.each(category.entries, function(index, testcase) {
                        var li = $('<li class="test_case_item"></li>');
                        var state = state_name[testcase.state];
                        var assignee = testcase.assignee || 'unassigned';
                        var unassigned = assignee === 'unassigned' ? ' unassigned' : '';
                        $(li)
                            .append('<span class="state ' + state + '">' + state_label[state] + '</span>')
                            .append('<span class="test_name">' + testcase.test_name + '</span>')
                            .append('<span class="assignee' + unassigned + '">' + assignee + '</span>');
                        $(ul)
                            .append(li);
                        $(li)
                            .click(function(e) {
                                load_test_case(testcase);
                            });
                    });
                });
                $('#content_area')
                    .append('<button>Import new Test Cases to this Run</button>')
                    .find('button')
                    .button()
                    .click(function() {
                        $('#content_area').html('Syncing test cases...');
                        $.ajax({
                            url: '/record/sync',
                            method: 'POST',
                            success: function(data) {
                                load_test_cases();
                            },
                            error: function(data) {
                                $('#content_area').html('Syncing test cases failed.');
                            },
                        });
                    });
            },
            error: function(data) {
                $('#test_list').html('<p class="error">Failed to load test cases</p>');
            },
        });
    };

    $('#list_test_cases_button')
        .button()
        .click(function() {
            load_test_cases();
        });

    var load_test_case = function(testcase) {
        var assignee = testcase.assignee || 'no one';
        var unassigned = assignee === 'unassigned' ? ' unassigned' : '';
        var state = state_name[testcase.state];
        $('#content_header')
            .html('<span class="state ' + state + '">' + state_label[state] + '</span>')
            .append('<span class="title">' + testcase.test_category + ' / ' + testcase.test_name + '</span>');
        if (assignee !== 'no one') {
            $('#content_header')
                .append(' (assigned to <span class="assignee">' + assignee + '</span>)');
        }
        $('#content_area')
            .html('<div id="content_md"></div>' +
                  '<div id="content_input"></div>' +
                  '<div id="content_history"></div>'
            );
        $.ajax({
            url: testcase.url,
            success: function(data) {
                $('#content_md').html(markdown.makeHtml(data));
            },
            error: function(data) {
                $('#content_area').html(data);
            },
        });
        build_op_buttons(testcase.test_category, testcase.test_name);
        $.ajax({
            url: testcase.history_url,
            success: function(data) {
                $('#jira_input').val(data.current.jira || '');
                $('#comment_input').val(data.current.comment || '');
                var ul = $('<ul class="test_case_list"></ul>');
                $('#content_history')
                    .append('<h2>History</h2>')
                    .append(ul);
                $.each(data.entries, function(index, testcase) {
                    var li = $('<li class="test_case_item"></li>');
                    var state = state_name[testcase.state];
                    var assignee = testcase.assignee || 'unassigned';
                    var unassigned = assignee === 'unassigned' ? ' unassigned' : '';
                    var comment = testcase.comment;
                    var jira = testcase.jira;
                    $(li)
                        .append('<span class="state ' + state + '">' +
                                state_label[state] + '</span>')
                        .append('<span class="assignee' + unassigned + '">' + assignee + '</span>')
                        .append(' <span class="ts">' + testcase.ts + '</span>');
                    $(ul)
                        .append(li);
                    if (comment !== null || jira !== null) {
                        var subul = $('<ul class="test_case_sublist"></ul>');
                        if (comment !== null) {
                            $(subul)
                                .append('<li class="test_case_subitem">Comment: ' + comment + '</li>');
                        }
                        if (jira !== null) {
                            $(subul)
                                .append('<li class="test_case_subitem">Jira: <a href="' + jira + '">' + jira + '</a></li>');
                        }
                        $(li)
                            .append(subul);
                    }
                });
            },
            error: function(data) {
            },
        });
    };

    var build_op_buttons = function(category, test_name) {
        $('#content_input')
            .append(
                '<h2>Feedback</h2>' +
                '<div class="label">Jira ticket url</div>' +
                '<input type="text" maxlength="100" id="jira_input">' +
                '<div class="label">Brief comment</div>' +
                '<input type="text" maxlength="200" id="comment_input">'
            );

        var ops_area = $('#content_input')
            .append('<div id="ops_area"></div>')
            .find('#ops_area');

        $.each(['assigned', 'passed', 'failed', 'blocked', 'skipped', 'not_run'], function(index, state) {
            ops_area
                .append('<button id="op_' + state + '">' + state_verb[state] + '</button>')
                .find('#op_' + state)
                .button()
                .click(function() {
                    $.ajax({
                        url: '/record/op/' + category + '/' + test_name + '/' + state,
                        method: 'PUT',
                        data: JSON.stringify({
                            jira: $('#jira_input').val(),
                            comment: $('#comment_input').val(),
                        }),
                        contentType: "application/json",
                        success: function(data) {
                            load_test_case(data);
                        },
                        error: function(data) {
                            alert('ERROR');
                        },
                    });
                });

        });
    };

    load_token_info();
    load_test_cases();
});
