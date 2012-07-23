var path;

function switchPage() {
	$('.page').hide();
	path = window.location.pathname.split('/');
	var page = $('#' + path[1]);
	if (page.length != 1) navigate("/user/9a031641-2065-4481-b890-4ab9a33d793a");  // FIXME: Use something else
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
				$('#userpage')[0].innerHTML = data;
			},
			error: function(xhr, textStatus, errorThrown) { alert("Unable to get user: " + errorThrown); },
		};
		$.ajax(settings);		
	});
	$('#pagenav a').on('click', function(ev) {
		ev.preventDefault();
		navigate(this.href);
	});
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
			if (d && d.url) navigate(d.url);
		},
		error: function(xhr, textStatus, errorThrown) { alert("Unable to submit form: " + errorThrown); },
		complete: function() { submit.removeAttr('disabled'); }
	};
	$.ajax(settings);
})
