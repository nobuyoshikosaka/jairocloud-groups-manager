// Application configuration for client side
/* eslint-disable @stylistic/max-len */

/**
 * Server hostname of this application \
 * [Mandatory]
 */
const serverName = 'localhost' as string

/**
 * Base URL of this application \
 * [Mandatory]
 */
const baseURL = `https://${serverName}` as string

const header = {
  /**
   * Path to the logo image file \
   * Example: "/logo.png" \
   * [Mandatory]
   */
  serviceLogo: '/logo.png' as string,

  /**
   * Alt name for the logo image file \
   * [Mandatory]
   */
  serviceAltName: 'JAIRO Cloud Groups Manager' as string,
}

const table = {
  /**
   * Options for page size selection in tables
   */
  pageSize: {
    repositories: [20, 50, 100] as number[],
    groups: [20, 50, 100] as number[],
    users: [20, 50, 100] as number[],
  },
}

const repositories = {
  /**
   * Maximum length of the URL ID entered in the repository creation form \
   * (excluding “https://”, the “jc_” prefix assigned to the ID, and additional padding) \
   * [Mandatory]
   */
  maxUrlLength: 50 - 'https://'.length - 'jc_'.length - 9,
}

const groups = {
  /**
   * Maximum length of the URL ID entered in the group creation form \
   * (excluding the “jc_” prefix assigned to the ID and additional padding) \
   * [Mandatory]
   */
  maxUrlLength: 50 - 'jc_'.length - '_groups_'.length - 4,
}

const wayf = {
  /**
   * URL of the WAYF to use \
   * Examples: "https://wayf.switch.ch/SWITCHaai/WAYF", "https://wayf-test.switch.ch/aaitest/WAYF"; \
   * [Mandatory]
   */
  URL: 'https://test-ds.gakunin.nii.ac.jp/WAYF' as string,

  /**
   * URL of the JavaScript file to write embedded WAYF \
   * [Mandatory]
   */
  jsURL: 'https://test-ds.gakunin.nii.ac.jp/WAYF/embedded-wayf.js' as string,

  /**
   * EntityID of the Service Provider that protects this Resource Server \
   * Examples: "https://econf.switch.ch/shibboleth", "https://dokeos.unige.ch/shibboleth" \
   * [Mandatory]
   */
  spEntityID: `${baseURL}/shibboleth-sp` as string,

  /**
   * Shibboleth Service Provider handler URL \
   * Examples: "https://point.switch.ch/Shibboleth.sso", "https://rr.aai.switch.ch/aaitest/Shibboleth.sso" \
   * [Mandatory, if wayf_use_discovery_service = false]
   */
  spHandlerURL: `${baseURL}/Shibboleth.sso` as string,

  /**
   * URL on this resource that the user shall be returned to after authentication \
   * Examples: "https://econf.switch.ch/aai/home", "https://olat.uzh.ch/my/courses" \
   * [Mandatory]
   */
  returnURL: `${baseURL}/Shibboleth.sso/Session` as string,

  /**
   * Most used Identity Providers will be shown as top category in the drop down \
   * list if this feature is used. \
   * [Optional, commented out by default] \
   * var wayf_most_used_idps =  new Array("https://aai-logon.unibas.ch/idp/shibboleth", "https://aai.unil.ch/idp/shibboleth");
   */
  mostUsedIdps: [
  ] as string[],

  /**
   * Categories of Identity Provider that shall not be shown \
   * Possible values are: "hokkaido","tohoku","kanto","chubu","kinki","chugoku","shikoku","kyushu","others", "all" \
   * Example of how to hide categories \
   * var wayf_hide_categories =  new Array("other", "library"); \
   * [Optional, commented out by default]
   */
  hideCategories: [] as string[],

  /**
   * EntityIDs of Identity Provider whose category is hidden but that shall be shown anyway \
   * If this array is not empty, wayf_show_categories will be disabled because \
   * otherwise, unhidden IdPs may be displayed in the wrong category \
   * Example of how to unhide certain Identity Providers \
   * var wayf_unhide_idps = new Array("https://aai-login.uzh.ch/idp/shibboleth"); \
   * [Optional, commented out by default]
   */
  unhideIdps: [
  ] as string[],

  /**
   * EntityIDs of Identity Provider that shall not be shown at all \
   * Example of how to hide certain Identity Provider \
   * var wayf_hide_idps = new Array("https://idp.unige.ch/idp/shibboleth", "https://lewotolo.switch.ch/idp/shibboleth"); \
   * [Optional, commented out by default]
   */
  hideIdps: [
  ] as string[],

  /**
   * EntityIDs, Names and SSO URLs of Identity Providers from other federations \
   * that shall be added to the drop-down list \
   * The IdPs will be displayed in the sequence they are defined \
   * [Optional, commented out by default]
   */
  additionalIdPs: [
    { name: 'Orthros-Test', entityID: 'https://core-stg.orthros.gakunin.nii.ac.jp/idp' },
  ] as { name: string, entityID: string }[],
}

export default {
  /** Server hostname of this application */
  serverName,
  /** Base URL of this application */
  baseURL,
  /** Header configuration */
  header,
  /** Table configuration */
  table,
  /** Repository configuration */
  repositories,
  /** WAYF (Embedded DS) configuration */
  wayf,
}
