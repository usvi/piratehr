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
	if (localStorage['auth']) navigate("/user/", true);  // Note: user page re-redirects to specific uuid
	else navigate("/register/", true);
}

$(document).ready(function() {
	$(window).on("popstate", switchPage);
	$('input[type=text],input[type=tel],input[type=email]').addClass('inputfield');
	$('input[type=submit]').addClass('inputsubmit');
	$('#user').on('show', function() {
		auth = localStorage['auth'];
		var uuid = path[2];
		// Handling for /user/ without uuid
		if (!uuid) {
			if (!auth) { redirects(); return; }
			a = JSON.parse(auth);
			path[2] = a.uuid;
			navigate(path.join('/'), true);
			return;
		}
		// Request user data
		data = {};
		if (auth) data.auth = auth;
		form = $('#userform');
		url = form.attr('action').replace('[uuid]', uuid);
		var settings = {
			data: JSON.stringify(data),
			url: url,
			type: "PROPFIND",
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
	$('#pagenav a').on('click', function(ev) {
		ev.preventDefault();
		navigate(this.href);
	});
	switchPage();
	updateAuth();
	showOrgPages();
	$('#auth_logout').on('click', logout);
	$('#org').on('show', showOrgPages);
	$(document).ajaxError(ajaxError);
});

function ajaxError(e, xhr, textStatus, errorThrown) {
	if (xhr.status == 401) {
		storage = localStorage["auth"];
		if (storage) logout("Your session has expired and you need to login again.");
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
	jsonQuery("", "/api/organization.json", "PROPFIND", function(data, textStatus, xhr) {
		var r = JSON.parse(data);
		$('#orglisttable').children().remove();
		for (var key in r) {
			var org_link = "<a href=\"/org/" + r[key].friendly_name + "\">" +  r[key].friendly_name + "</a>"
			var table_row = "<tr><td>" + org_link + "</td></tr>";
			$('#orglisttable').append(table_row);
		}
	}, undefined);
}


function loadOrgDetails(inputOrgFriendly) {
	jsonQuery("", "/api/organization_" + inputOrgFriendly + ".json", "PROPFIND", function(data, textStatus, xhr) {
		var r = JSON.parse(data);
		$('#orgdetails_friendly_name').text(r.friendly_name);
		$('#orgdetails_legal_name').text(r.friendly_name);
	}, undefined);
}


function showOrgPages() {
	$('.org').hide();
	loadOrgList();
	//$('#orgdetails').on('show', loadOrgDetails())
	if(path[2]) { // We have org friendly_name
		loadOrgDetails(path[2]); // Load, and..
		$('#orgdetails').show(); // show them all in place
	} else {
		$('#orglist').show();
	}
}


function login(auth) {
	localStorage["auth"] = JSON.stringify(auth);
	flash("Login successful");
	updateAuth();
}

function logout(msg) {
	localStorage.removeItem("auth");
	flash(msg || "You have been logged out. Close this page and clear history to remove any remaining sensitive data.");
	updateAuth();
	$('#authform input[name=login]').focus();
}

function updateAuth() {
	var storage = localStorage["auth"];
	if (storage) {
		auth = JSON.parse(storage);
		$('#authform').hide();
		$('#authinfo').show();
		$('#auth_name').text(auth.name + " logged in");
	} else {
		$('#authform').show();
		$('#authinfo').hide();
		$('#auth_name').empty();
	}
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
	auth = localStorage['auth'];
	if (auth) data.auth = auth;
	var settings = {
		data: JSON.stringify(data),
		url: form.attr('action'),
		type: form.attr('method'),
		contentType: "application/json",
		success: function(data, textStatus, xhr) {
			if (xhr.type == 'POST') form[0].reset();  // Clear the form after successful POST
			var d = JSON.parse(data);
			if (d) {
				if (d.user_url) navigate(d.user_url);
				if (d.auth) login(d.auth);
				if (d.status) flash(status);
			}
		},
		complete: function() { submit.removeAttr('disabled'); }
	};
	$.ajax(settings);
})

