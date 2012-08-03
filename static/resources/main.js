var path;

function flash(msg) {
	var elem = $('#flash');
	var p = $('<p>');
	p.text(msg);
	setTimeout(function() { p.slideUp('slow', function() { p.remove() }); }, Math.min(2000 + 10 * (msg || '').length, 10000));
	p.appendTo(elem[0]);
	elem.slideDown('slow');
	elem.click(function () { $(this).slideUp('fast') });
}

var g = {};  // Global variables go in here

function switchPage() {
	if (g.page_location == window.location.href) return;  // Nothing to do
	g.page_location = window.location.href;
	g.page = {};  // Page-specific settings go here
	$('.page').hide();
	path = window.location.pathname.split('/');
	var page = $('#' + path[1]);
	g.page.arg1 = path[2];
	g.page.arg2 = path[3];
	// Test if the URL mapped to a page, otherwise redirect
	if (page.length != 1) { redirects(path); return; }
	// Activate the page specified by URL
	page.show();
	$(page).trigger("show");
}

function redirects() {
	// Smart(?) redirect from UUID URL to some actual page
	if (path[1] == 'uuid') {
		path[1] = 'user';
		navigate(path.join('/'), true);
		return;
	}
	// Non-existing page, redirect...
	if (path.length > 2 /* not root */) flash(path.join('/') + " not found, redirecting...");
	if (g.auth) navigate("/user/", true);  // Note: user page re-redirects to specific uuid
	else navigate("/register/", true);
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
	// Set some classes (avoid tedious repeat in HTML)
	$('input[type=text],input[type=tel],input[type=email],input[type=datetime]').addClass('inputfield');
	$('input[type=submit]').addClass('inputsubmit');
	// When user page is shown, load data...
	$('#user').on('show', function() {
		// Handling for /user/ without uuid
		if (!path[2]) {
			if (!g.auth) { redirects(); return; }
			path[2] = g.auth.uuid;
			navigate(path.join('/'), true);
			return;
		}
		g.page.uuid = path[2];
		// Request user data
		form = $('#userform');
		var settings = {
			url: form.attr('action'),
			type: 'GET',
			contentType: "application/json",
			dataType: 'json',
			success: function(data, textStatus, xhr) {
				if (g.page.uuid != data.uuid) { flash("Unexpected UUID returned by server"); return; }
				for (var key in data) {
					var elem = $('input[name=' + key + ']', form)[0];
					if (elem) $(elem).attr('value', data[key] || '');
					//else flash("Warning: Value ignored: " + key + "=" + data[key]);
				}
				if (data.uuid_url) {
					$('#qrcode', form).remove();
					var qr = qrcode(4, 'L');
					qr.addData(data.uuid_url);
					qr.make();
					input = $('input[name=uuid]', form);
					input.before('<a id=qrcode href="' + data.uuid_url + '">' + qr.createImgTag() + '<br></a>');
				}
			},
		};
		settings.url = settings.url.replace('[uuid]', g.page.uuid);
		$.ajax(settings);		
	});
	$('#org').on('show', showOrgPages);
	// Do not actually load pagenav links, only switch URL
	$('#pagenav a').on('click', function(ev) {
		ev.preventDefault();
		navigate(this.href);
	});
	// Display organization create form when button clicked
	$('#orgcreatebutton').on('click', function(ev) {
		ev.preventDefault();
		var field = $('#orgcreatefield');
		var url = '/org/' + field.attr('value');
		field.attr('value', '');
		navigate(url);
	});
	// Load proper page
	switchPage();
});

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

function loadOrgList() {
	jsonQuery("", "/api/organizations.json", "GET", function(data, textStatus, xhr) {
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
				navigate(this.href, true);
			});
			// Add table row
			$('#orglisttable').append($('<tr>').append($('<td>').append(anchor)).append($('<td>').text(org.friendly_name)));
		}
	}, undefined);
}


function loadOrgData(orgname) {
	jsonQuery("", "/api/organization_" + orgname + ".json", "GET", function(data, textStatus, xhr) {

		$('#childlisttable').empty();
		$('#org_parent_link').html("");
		form = $('#orgform');
		for (var key in data) {
			value = data[key]
			var elem = $('input[name=' + key + ']', form)[0];
			if (!elem) elem = $('select[name=' + key + ']', form)[0];
			if (elem) $(elem).attr('value', value || '');
			//else flash("Warning: Value ignored: " + key + "=" + value);
		}
		for (var key in data.child_orgs) {
			var table_row = "<tr><td>";
			table_row += "<a href=/org/" + data.child_orgs[key].perma_name + ">" + data.child_orgs[key].friendly_name + "</a>";
			table_row += "</td></tr>";
			$('#childlisttable').append(table_row);
			// Fetch the reference and append function for navigation manipulation
			$('#childlisttable').find('tr:last').eq(0).find('a').on('click', function(ev) {
				ev.preventDefault();
				navigate(this.href, true);
			});

		}
		if(data.child_orgs) {
			$('#orgdetails_child_organizations').show(); // Show children if they exist.
		}
		if (data.parent_org) {
			$('#org_parent_link').html("<small><small>Parent: <a href=/org/" + data.parent_org.perma_name + ">" +
				data.parent_org.friendly_name + "</a></small></small>");
			// Add navigation manipulation for parent also if parent exists
			$('#org_parent_link').find('a').on('click', function(ev) {
				ev.preventDefault();
				navigate(this.href, true);
			});
		}
		$('#orgdetails').show();
	}, undefined);
}


function showOrgPages() {
	$('.org').hide();
	loadOrgList();
	if(path[1] == "org" && path[2]) { // We have org friendly_name
		$('#orgedit').show();
		loadOrgData(path[2]);
	} else {
		$('#orglist').show();
	}
}

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
		else flash(data.description);
	}
	$.ajax(settings);
})

