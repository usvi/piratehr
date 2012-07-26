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

var oldPage;

function switchPage() {
	if (oldPage == window.location.href) return;  // Nothing to do
	oldPage = window.location.href;
	$('.page').hide();
	path = window.location.pathname.split('/');
	var page = $('#' + path[1]);
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
	flash(path.join('/') + " not found, redirecting...");
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
	$('input[type=text],input[type=tel],input[type=email]').addClass('inputfield');
	$('input[type=submit]').addClass('inputsubmit');
	// When user page is shown, load data...
	$('#user').on('show', function() {
		var uuid = path[2];
		// Handling for /user/ without uuid
		if (!uuid) {
			if (!g.auth) { redirects(); return; }
			path[2] = g.auth.uuid;
			navigate(path.join('/'), true);
			return;
		}
		// Request user data
		form = $('#userform');
		url = form.attr('action').replace('[uuid]', uuid);
		var settings = {
			url: url,
			type: "GET",
			contentType: "application/json",
			success: function(data, textStatus, xhr) {
				var r = JSON.parse(data);
				if (uuid != r.uuid) { flash("Unexpected UUID returned by server"); return; }
				for (var key in r) {
					var elem = $('input[name=' + key + ']', form)[0];
					if (elem) $(elem).attr('value', r[key] || '');
					//else flash("Warning: Value ignored: " + key + "=" + r[key]);
				}
				if (r.uuid_url) {
					$('#qrcode', form).remove();
					var qr = qrcode(4, 'L');
					qr.addData(r.uuid_url);
					qr.make();
					input = $('input[name=uuid]', form);
					input.before('<a id=qrcode href="' + r.uuid_url + '">' + qr.createImgTag() + '<br></a>');
				}
			},
		};
		$.ajax(settings);		
	});
	$('#org').on('show', showOrgPages);
	// Do not actually load pagenav links, only switch URL
	$('#pagenav a').on('click', function(ev) {
		ev.preventDefault();
		navigate(this.href);
	});
	// Display rganization create form when button clicked
	$('#orgcreatebutton').on('click', function(ev) {
		$('#orglist').hide();
		$('#orgcreateform').show();
	});
	// Load proper page
	switchPage();
	showOrgPages();
});

// Insert authentication data to requests
function ajaxSend(ev, xhr){
	if (g.authstr) xhr.setRequestHeader("Authorization", "Basic " + $.base64.encode("json:" + g.authstr));
}

// Handle common errors
function ajaxError(e, xhr, textStatus, errorThrown) {
	if (xhr.status == 401) {
		if (g.auth) logout("Your session has expired and you need to login again.");
		else flash("You need to be logged in to access this function.");
		return;
	}
	flash(errorThrown + ": " + xhr.responseText);
}


function jsonQuery(inputData, inputUrl, inputType, successFunc, completeFunc) {
	var settings = {
		data: JSON.stringify(inputData),
		url: inputUrl,
		type: inputType,
		contentType: "application/json",
		success: successFunc,
		complete: completeFunc
	};
	$.ajax(settings);
}


function loadOrgList() {
	jsonQuery("", "/api/organization.json", "GET", function(data, textStatus, xhr) {
		var r = JSON.parse(data);
		$('#orglisttable').children().remove();
		for (var key in r) {
			var org_link = "<a href=\"/org/" + r[key].perma_name + "\">" +  r[key].friendly_name + "</a>"
			var table_row = "<tr><td>" + org_link + "</td></tr>";
			$('#orglisttable').append(table_row);
		}
	}, undefined);
}


function loadOrgDetails(inputOrgFriendly) {
	jsonQuery("", "/api/organization_" + inputOrgFriendly + ".json", "GET", function(data, textStatus, xhr) {
		var r = JSON.parse(data);
		var child_orgs = "Children: ";
		$('#orgdetails_friendly_name').text(r.main_org.friendly_name); 
		$('#orgdetails_legal_name td').eq(1).text(r.main_org.legal_name); // Pick 2nd column beginning from the row and change.
		for (var key in r.child_orgs) {
			child_orgs += r.child_orgs[key].friendly_name + ", ";
		}
		if (r.parent_org) {
		}
	}, undefined);
}


function showOrgPages() {
	$('.org').hide();
	loadOrgList();
	//$('#orgdetails').on('show', loadOrgDetails())
	if(path[1] == "org" && path[2]) { // We have org friendly_name
		$('#orgdetails_parent_organization').hide() // Hide everything first
		$('#orgdetails_child_organizations').hide()
		loadOrgDetails(path[2]); // Load, and..
		$('#orgdetails').show(); // show them all in place
	} else {
		$('#orglist').show();
	}
}

function login(authstr, msg) {
	try {
		g.auth = JSON.parse(authstr);
	} catch (err) {
		logout();
		return;
	}
	g.authstr = authstr;
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
	settings.success = function(data, textStatus, xhr) {
		if (settings.type == 'POST') form[0].reset();  // Clear the form after successful POST
		if (settings.type == 'PUT') form[0].reset();  // Clear the form after successful PUT
		if (settings.url.split('/').pop() == 'auth.json') login(JSON.stringify(data), "Login successful");
	}
	$.ajax(settings);
})

