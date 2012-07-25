var path;

function flash(msg) {
	var elem = $('#flash');
	var p = $('<p>');
	p.text(msg);
	setTimeout(function() { p.slideUp('slow', function() { p.remove() }); }, Math.min(2000 + 10 * msg.length, 10000));
	p.appendTo(elem[0]);
	elem.slideDown('slow');
	elem.click(function () { $(this).slideUp('fast') });
}

var oldPage;

function switchPage() {
	if (oldPage == window.location.href) return;  // Nothing to do
	oldPage = window.location.href;
	$('.page').hide();
	$('.ajaxfield').empty();
	path = window.location.pathname.split('/');
	var page = $('#' + path[1]);
	if (page.length != 1) navigate("/register/");
	else page.show();
	$(page).trigger("show");
}

$(document).ready(function() {
	$(window).on("popstate", switchPage);
	$('input[type=text],input[type=phone],input[type=email]').addClass('inputfield');
	$('input[type=submit]').addClass('inputsubmit');
	$('#user').on('show', function() {
		var uuid = path[2];
		if (uuid == null) return;
		data = {};
		auth = localStorage['auth'];
		if (auth) data.auth = auth;
		var settings = {
			data: JSON.stringify(data),
			url: "/api/user_" + uuid + ".json",
			type: "PROPFIND",
			contentType: "application/json",
			success: function(data, textStatus, xhr) {
				var r = JSON.parse(data);
				if (uuid != r.uuid) { flash("Unexpected UUID returned by server"); return; }
				for (var key in r) {
					var elem = $('#user_' + key)[0];
					if (elem) $(elem).text(r[key] || '');
					//else flash("Warning: Value ignored: " + key + "=" + r[key]);
				}
				var qr = qrcode(4, 'L');
				qr.addData(r.user_url);
				qr.make();
				$('#user_uuid').prepend('<a href="' + r.user_url + '" onclick="return false">' + qr.createImgTag() + '</a><br>');
			},
			error: function(xhr, textStatus, errorThrown) { flash("Unable to get user: " + errorThrown); },
		};
		$.ajax(settings);		
	});
	$('#pagenav a').on('click', function(ev) {
		ev.preventDefault();
		navigate(this.href);
	});
	switchPage();
	updateAuth();
	prepareOrgPages();
	$('#auth_logout').on('click', logout);
	$('#org').on('show', prepareOrgPages);
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

function prepareOrgPages() {
	loadOrgList();
	if(path[2]) { // We have org id
		$('#orgdetails').show();
	} else {
		$('#orglist').show();
	}
}

function loadOrgList() {
	flash("Loading organization list");
	var settings = {
		data: "",
		url: "/api/organization.json",
		type: "PROPFIND",
		contentType: "application/json",
		success: function(data, textStatus, xhr) {
			var ds = "";
			var r = JSON.parse(data);
			$('#orglisttable').children().remove();
			for (var key in r) {
				var org_link = "<a href=\"/org/" + r[key].id + "\">" +  r[key].legal_name + "</a>"
				var table_row = "<tr><td>" + org_link + "</td></tr>";
				$('#orglisttable').append(table_row);
			}
		},
		error: function(xhr, textStatus, errorThrown) { flash("Unable to get organizations: " + errorThrown); },
	};
	$.ajax(settings);
}

function login(auth) {
	localStorage["auth"] = JSON.stringify(auth);
	flash("Login successful");
	updateAuth();
}

function logout(msg) {
	localStorage.removeItem("auth");
	flash(msg || "You have been logged out. Close this page and clear history to remove any remaining sensitive data.");
	$('#authform').focus();
	updateAuth();
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

function navigate(url) {
	// Allow for current events to finish before navigating
	window.setTimeout(function() {
		// Navigate without reloading if the browser supports it
		if (history.pushState) history.pushState(null, null, url);
		else window.location(url);
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
			form[0].reset();  // Clear the form
			var d = JSON.parse(data);
			if (d) {
				if (d.user_url) navigate(d.user_url);
				if (d.auth) login(d.auth);
				if (d.status) flash(status);
			}
		},
		error: function(xhr, textStatus, errorThrown) { flash(errorThrown + ": " + xhr.responseText); },
		complete: function() { submit.removeAttr('disabled'); }
	};
	$.ajax(settings);
})

