// This Source Code Form is subject to the terms of the Mozilla Public
// License, v. 2.0. If a copy of the MPL was not distributed with this
// file, You can obtain one at http://mozilla.org/MPL/2.0/.

(function () {

$(document).ready(function () {
    $('select').on('change', rankChanged);
    $('select').on('change', updateSummary).change();
});

function rankChanged(e) {
    var value = $(e.target).val();
    if (value !== '0') {
        $('select').not(e.target).each(function () {
            if ($(this).val() === value) {
                $(this).val((+value) + 1);
                $(this).change();
            }
        });
    }
}

function toInt(x) {
    var i = parseInt(x, 10);
    return x === i.toString() ? i : null;
}

function intKeys(o) {
    // Return the integral keys of the object o.
    var rv = [];
    for (var k in o) {
        if (o.hasOwnProperty(k) && toInt(k) !== null) {
            rv.push(toInt(k));
        }
    }
    return rv;
}

function numericSort(a, b) { return a - b; }

// Truncate an array at index; arr[index] and everything after is removed.
function truncate(arr, index) { arr.splice(index, arr.length - index); }

function updateSummary() {
    // Preference 0 is "unranked"; indices here are weird because 0 is special.
    var prefs = {0: 'dummy'};
    var conflict = 0;
    $('select').each(function () {
        var rank = toInt($(this).val());
        if (rank && prefs[rank]) conflict = Math.min(conflict, rank);
        prefs[rank] = $('label[for="'+this.id+'"]').text();
    });
    var keys = intKeys(prefs).sort(numericSort);
    var gap = !(keys[keys.length - 1] === keys.length - 1);
    
    // Truncate the list of keys at the point of the error.  (Ballots are valid
    // up to the first error, so we need to show what will count.)
    if (conflict) truncate(keys, conflict);
    for (var i = 1; i < keys.length; ++i) {
        if (keys[i] !== i) {
            truncate(keys, i);
            break;
        }
    }

    var status;
    if (keys.length <= 1) {
        status = "<p>You have declined to vote for any representatives."
    } else if (keys[1] !== 1) {
        status = "<p>Your ballot for first-year representatives is spoiled " +
	         "because your rankings do not start from 1.";
    } else {
        var trunc_msg = ""; // for truncated ballots
        if (conflict) {
            trunc_msg = "<p>You ranked more candidates, but they will not be " +
                        "considered because two candidates have the same rank.";
        } else if (gap) {
            trunc_msg = "<p>You ranked more candidates, but they will not be " +
                        "considered because your rankings are not consecutive.";
        }
        var ballot = '<ol>';
        for (var i = 1; i < keys.length; ++i) {
            ballot += '<li>' + prefs[i] + '</li>';
        }
        ballot += '</ol>';
        ballot += trunc_msg;
        status = "<p>Your ballot for first-year representatives: " + ballot;
    }
    $('#directors-status').html(status);
}

})();
