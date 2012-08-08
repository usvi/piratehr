//
//  PAGE HANDLERS
//

$(document).ready(function() {
	$('#user').on('show', showUserPage);
	$('#memberships').on('show', showMembershipsPage);
	$('#org').on('show', showOrgPage);
	// Display organization create form when button clicked
	$('#orgcreatebutton').on('click', function(ev) {
		ev.preventDefault();
		var field = $('#orgcreatefield');
		var url = '/org/' + field.attr('value');
		field.attr('value', '');
		g.neworg = true;
		navigate(url);
	});
});

function showUserPage() {
	// Handling for /user/ without uuid
	if (!g.page.arg1) {
		if (!g.auth) { redirects(); return; }
		navigate('/user/' + g.auth.uuid, true);
		return;
	}
	// Load user data
	loadForm('#userform', function(form, data) {
		if (g.page.arg1 != data.uuid) { flash("Internal error: Unexpected UUID returned by server"); }
		// Add UUID to password change form
		if (data.uuid) $('#passwordform input[name=uuid]').attr('value', data.uuid);
		// Render QRCode
		if (data.uuid_url) {
			$('#qrcode', form).remove();
			var qr = qrcode(4, 'L');
			qr.addData(data.uuid_url);
			qr.make();
			input = $('input[name=uuid]', form);
			input.before($('<a id=qrcode>').attr('href', data.uuid_url).html(qr.createImgTag() + '<br>'));
		}
	});
}

function changeMembership(membershipOrg, operation) {
        jsonQuery({'operation':operation}, "/api/membership_" + membershipOrg + ".json", "POST", function(data, textStatus, xhr) {
                	showMembershipsPage();
                });
}

function showMembershipsPage() {
	jsonQuery(undefined, "/api/memberships.json", "GET", function(data, textStatus, xhr) {
		$('#membershiplisttable').children().remove();
		g.memberships = data;
		for (var key in g.memberships) {
			var button = $('<button>Apply for membership</button>');
			button.on('click', (function(perma_name) {
				return function(ev) {
					ev.preventDefault();
					changeMembership(perma_name, 'apply');
				}
			})(g.memberships[key].perma_name));
			var status = "Not a member";
			if (g.memberships[key].status != 'null') {
				button = $('<button>Resign</button>');
				status = g.memberships[key].status;
			}
			$('#membershiplisttable').append($('<tr>'));
			$('#membershiplisttable').find('tr:last').append($('<td>').append(g.memberships[key].friendly_name));
			$('#membershiplisttable').find('tr:last').append($('<td>').append(status));
			$('#membershiplisttable').find('tr:last').append($('<td>').append(button));
		}
	});
}

function showOrgPage() {
	$('.org').hide();
	loadOrgList();
	if (g.page.arg1) {  // We are viewing some specific org
		$('#orgedit').show();
		if (!g.neworg) loadForm('#orgform');
		g.neworg = false;
	} else {  // List of all orgs
		$('#orglist').show();
	}
}

function loadOrgList() {
	jsonQuery(undefined, "/api/organizations.json", "GET", function(data, textStatus, xhr) {
		g.orgs = data.organizations;
		// Clear any old data
		$('#parent_select').children().remove();
		$('#parent_select').append($('<option>').attr('value', '').text('(No parent)'));
		$('#orglisttable').children().remove();
		for (var key in g.orgs) {
			var org = g.orgs[key];
			// Update organization create form parent options
			$('#parent_select').append($('<option>').attr('value', org.perma_name).text(org.friendly_name));
			// Add a row to organization table
			var anchor = $('<a>');
			anchor.attr('href', '/org/' + org.perma_name);
			anchor.attr('id', 'organization_' + org.perma_name);
			anchor.text(org.perma_name);
			// AJAX navigation
			anchor.on('click', function(ev) {
				ev.preventDefault();
				navigate(this.href);
			});
			// Add table row
			$('#orglisttable').append($('<tr>').append($('<td>').append(anchor)).append($('<td>').text(org.friendly_name)));
		}
	});
}


//
//  CORE LOGIC
//

function login(authstr, msg) {
	g.authstr = authstr;
	try { g.auth = JSON.parse(authstr); } catch (err) {}
	if (!g.authstr || !g.auth) { logout(); return; }  // Login info missing or invalid, just logout...
	localStorage['auth'] = authstr;
	if (msg) flash(msg);
	$('#authform').hide();
	$('#authinfo').show();
	$('#auth_name').text(g.auth.name);
}

function logout(msg) {
	localStorage.removeItem('auth');
	delete g.auth;
	delete g.authstr;
	if (msg) flash(msg);
	$('#authform').show();
	$('#authinfo').hide();
	$('#auth_name').empty();
	$('#authform input[name=login]').focus();
}

function switchPage() {
	if (g.page_location == window.location.href) return;  // Nothing to do
	g.page_location = window.location.href;
	g.page = {};  // Page-specific settings go here
	$('.page').hide();
	var path = window.location.pathname.split('/');
	g.page.base = path[1];
	g.page.arg1 = path[2];
	g.page.arg2 = path[3];
	// Test if the URL mapped to a page, otherwise redirect
	var page = $('#' + g.page.base);
	if (page.length != 1) return redirects();
	// Activate the page specified by URL
	page.show();
	$(page).trigger("show");
}

function redirects() {
	var base = g.page.base;
	// Smart(?) redirect from UUID URL to some actual page
	if (base == 'uuid') return navigate('/user/' + g.page.arg1, true);
	// Password reset URL
	if (base == 'reset') {
		jsonQuery({'type':'login_token','token':g.page.arg1}, '/api/auth.json', 'POST', function(data, textStatus, xhr) {
			login(JSON.stringify(data), 'Logged in. Change your password now');
			navigate('/user/' + g.auth.uuid, true);
		});
		return;
	}
	// Non-existing page, redirect...
	if (base /* not root */) flash('Page ' + base + ' not found, redirecting...');
	navigate(g.auth ? '/user/' + g.auth.uuid : '/register/', true);
}

$(document).ready(function() {
	// AJAX handlers
	$(document).ajaxSend(ajaxSend);
	$(document).ajaxError(ajaxError);
	// Restore session from Local Storage
	login(localStorage['auth']);
	$('#auth_logout').on('click', function(ev) {
		logout("You have been logged out. Close this page and clear history to remove any remaining sensitive data.");
	});
	// Make back/forward call switchPage
	$(window).on("popstate", switchPage);
	// Do not actually load pagenav links, only switch URL
	$('#pagenav a').on('click', function(ev) {
		ev.preventDefault();
		navigate(this.href);
	});
	// Set some classes (avoid tedious repeat in HTML)
	$('input[type=text],input[type=tel],input[type=email],input[type=datetime],input[type=password]').addClass('inputfield');
	$('input[type=submit]').addClass('inputsubmit');
	// Load proper page
	switchPage();
});


//
//  HELPER FUNCTIONS
//

var g = {};  // Global variables go in here

function navigate(url, redirect) {
	// Allow for current events to finish before navigating
	window.setTimeout(function() {
		// Navigate without reloading if the browser supports it
		if (history.pushState) {
			if (redirect) history.replaceState(null, null, url);
			else history.pushState(null, null, url);
		} else window.location(url);
		$(window).trigger("popstate");  // Not fired automatically, it seems
	}, 0);
}

$('.ajaxform').submit(function(ev) {
	ev.preventDefault();
	var form = $(this);
	var submit = $('input[type=submit]', this);
	submit.attr('disabled', 'disabled');  // Disable form while submission is in progress
	data = form.formParams();
	var settings = {
		data: JSON.stringify(data),
		dataType: 'json',
		url: form.attr('action'),
		type: form.attr('method'),
		contentType: "application/json",
		complete: function() { submit.removeAttr('disabled'); }
	};
	if (settings.url.indexOf("[arg1]") != -1) {
		if (!g.page.arg1) flash("Internal error: arg1 is not set");
		settings.url = settings.url.replace('[arg1]', g.page.arg1);
	}		
	settings.success = function(data, textStatus, xhr) {
		if (settings.type == 'POST') form[0].reset();  // Clear the form after successful POST
		if (settings.url.split('/').pop() == 'auth.json') login(JSON.stringify(data), "Login successful");
		if (settings.url.split('/').pop() == 'new_user.json') {
			login(JSON.stringify(data.auth), "User created and logged in");
			navigate(data.uuid_url);
		} else flash(data.description);
	}
	$.ajax(settings);
})

function jsonQuery(inputData, inputUrl, inputType, successFunc, completeFunc) {
	var settings = {
		data: JSON.stringify(inputData),
		dataType: 'json',
		url: inputUrl,
		type: inputType,
		contentType: "application/json",
		success: successFunc,
		complete: completeFunc
	};
	$.ajax(settings);
}

// Insert authentication data to requests
function ajaxSend(ev, xhr) {
	if (g.authstr) xhr.setRequestHeader("Authorization", "Basic " + utf8_to_b64("json:" + g.authstr));
}

// Handle common errors
function ajaxError(e, xhr, textStatus, errorThrown) {
	if (xhr.status == 401) {
		if (g.auth) logout("Your session has expired and you need to login again.");
		else flash("You need to be logged in to access this function.");
		return;
	}
	type = xhr.getResponseHeader('Content-type');
	if (type == "application/json") {
		json = JSON.parse(xhr.responseText);
		flash(json.description);
	} else {
		flash(errorThrown + ": ");
		$('#debug').html(xhr.responseText);
	}
}

function formUrl(form) {
	var url = form.attr('action');
	if (g.page.arg1) url = url.replace('[arg1]', g.page.arg1);
	if (g.page.arg2) url = url.replace('[arg2]', g.page.arg2);
	return url;
}

// Load data into a form specified by selector string.
// If func is passed, func(form, data) gets called for additional processing.
function loadForm(selector, func) {
	form = $(selector);
	jsonQuery(undefined, formUrl(form), "GET", function(data, textStatus, xhr) {
		for (var key in data) {
			value = data[key]
			var elem = $('input[name=' + key + ']', form)[0];
			if (!elem) elem = $('select[name=' + key + ']', form)[0];
			if (elem) $(elem).attr('value', value || '');
			//else flash("Warning: Value ignored: " + key + "=" + value);
		}
		if (func) func(form, data);
	});
}

// Briefly display a message to inform the user of an action being taken or of the result of one
function flash(msg) {
	var elem = $('#flash');
	var p = $('<p>');
	p.text(msg);
	setTimeout(function() { p.slideUp('slow', function() { p.remove() }); }, Math.min(2000 + 10 * (msg || '').length, 10000));
	p.appendTo(elem[0]);
	elem.slideDown('slow');
	elem.click(function () { $(this).slideUp('fast') });
}

