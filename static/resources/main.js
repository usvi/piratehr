var path;

function flash(msg) {
	var elem = $('#flash');
	var p = $('<p>', {
		text: msg
	});
	setTimeout(function() { p.slideUp('slow', function() { p.remove() }); }, 2000);
	p.appendTo(elem[0]);
	elem.slideDown('slow');
	elem.click(function () { $(this).slideUp('fast') });
}

var oldPage;

function switchPage() {
	if (oldPage == window.location.href) return;  // Nothing to do
	oldPage = window.location.href;
	$('.page').hide();
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
		var settings = {
			data: "",
			url: "/api/user_" + uuid + ".json",
			type: "GET",
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
});

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
	var settings = {
		data: JSON.stringify(form.formParams()),
		url: form.attr('action'),
		type: form.attr('method'),
		contentType: "application/json",
		success: function(data, textStatus, xhr) {
			form[0].reset();  // Clear the form
			var d = JSON.parse(data);
			if (d && d.user_url) navigate(d.user_url);
		},
		error: function(xhr, textStatus, errorThrown) { flash("Unable to submit form: " + errorThrown); },
		complete: function() { submit.removeAttr('disabled'); }
	};
	$.ajax(settings);
})

