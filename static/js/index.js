function uploadPhotoAndSummarize() {
  // Clear out the previous summaries & show the upload indicator
  $('#summary').empty();
  $('#uploadPhotoFormImageInput').prop('disabled', true);
  $('#uploadPhotoIndicator').show();

  var formData = new FormData();
  formData.append('image', $('#uploadPhotoFormImageInput')[0].files[0]);
  $.ajax({
    type: "POST",
    url: "/summarize",
    data: formData,
    processData: false,
    contentType: false,
    cache: false,
    xhr: function() {
      var xhr = new window.XMLHttpRequest();
      xhr.upload.addEventListener("progress", function(evt) {
        if (evt.lengthComputable) {
          var percentComplete = evt.loaded / evt.total;
          percentComplete = parseInt(percentComplete * 100);
          $('#uploadPhotoPercent').text('' + percentComplete + '%');
          if (percentComplete === 100) {
            $('#uploadPhotoIndicator').hide();
            $('#summarizingIndicator').show();
          }
        }
      }, false);
      return xhr;
    },
    success: function(msg) {
      // For each line, create the image/text pair of UI elements and add to the container
      var resp = JSON.parse(msg);
      for (i = 0; i < resp.lines.length; ++i) {
        var img = '<img src="' + 'data:image/png;base64,' + (i < resp.images.length ? resp.images[i] : '') + '"/>';
        var imgDiv = '<div class="col-sm-auto summaryCell">' + img + '</div>';
        var textDiv = '<div class="col-md-auto summaryCell">' + resp.lines[i] + '</div>'
        $('#summary').append('<div class="row summaryRow">' +
          ((i % 2 == 0) ? imgDiv : textDiv) +
          ((i % 2 == 1) ? imgDiv : textDiv) +
          '</div>');
      }
    },
    error: function() {
      alert("Unable to add new page. Please try again later.");
    },
    complete: function() {
      $('#uploadPhotoFormImageInput').prop('disabled', false);
      $('#uploadPhotoFormImageInput').val('');
      $('#uploadPhotoIndicator').hide();
      $('#summarizingIndicator').hide();
    }
  });
}

function pageLoad() {
  $('#uploadPhotoFormImageInput').change(uploadPhotoAndSummarize);
}

window.addEventListener('load', pageLoad);
